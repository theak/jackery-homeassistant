"""API client for Jackery cloud services."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import inspect
import json
import logging
import threading
import time
import uuid
from typing import Optional

import requests
from Cryptodome.Cipher import AES, PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from Cryptodome.Util.Padding import pad

try:
    import aiomqtt
except ModuleNotFoundError:
    aiomqtt = None

try:
    import socketry
    from socketry.client import _mqtt_params as _socketry_mqtt_params
except ModuleNotFoundError as err:  # pragma: no cover - dependency provided in prod
    if err.name == "socketry":
        socketry = None
        _socketry_mqtt_params = None
    else:
        raise

_LOGGER = logging.getLogger(__name__)

_REDACT_KEYS = frozenset(
    {"token", "mqttPassWord", "password", "deviceSecret", "randomSalt", "bluetoothKey"}
)


def _redact(value):
    """Return a copy of an API payload with credential fields masked for logging."""
    if isinstance(value, dict):
        return {
            k: "**REDACTED**" if k in _REDACT_KEYS else _redact(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


class JackeryMqttSession:
    """Persistent single-connection MQTT session for Jackery API.

    Owns one long-lived ``aiomqtt.Client`` and routes incoming messages to the
    active pending-request future (queries / commands) or drops them as push
    data.  A single ``_operation_lock`` serialises publish+wait operations so
    response matching is unambiguous - only one in-flight MQTT request exists
    at a time.
    """

    _MAX_RECONNECT_DELAY = 30.0

    def __init__(self, api: "JackeryAPI") -> None:
        self._api = api
        self._client: "aiomqtt.Client | None" = None
        self._user_id: "str | None" = None
        self._loop_task: "asyncio.Task | None" = None
        self._running = False
        self._reconnect_delay = 1.0
        self._operation_lock = asyncio.Lock()
        self._pending_matcher: "callable | None" = None
        self._pending_future: "asyncio.Future | None" = None
        self._connected = asyncio.Event()
        self._push_handlers: dict[str, callable] = {}

    async def start(self) -> None:
        """Start the background reconnect loop."""
        self._running = True
        self._loop_task = asyncio.create_task(
            self._run_loop(), name="jackery_mqtt_session"
        )

    async def stop(self) -> None:
        """Cancel the background loop and clean up."""
        self._running = False
        if self._loop_task is not None:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except (asyncio.CancelledError, Exception):
                pass
            self._loop_task = None
        self._fail_pending(RuntimeError("MQTT session stopped"))

    async def _run_loop(self) -> None:
        """Reconnect loop - runs until stop() is called."""
        while self._running:
            try:
                params, user_id = self._api._build_mqtt_params()
                dev_topic = f"hb/app/{user_id}/device"
                async with aiomqtt.Client(**params) as client:
                    self._client = client
                    self._user_id = user_id
                    self._reconnect_delay = 1.0
                    await client.subscribe(dev_topic, qos=1)
                    self._connected.set()
                    _LOGGER.info("Jackery MQTT persistent session connected")
                    async for message in client.messages:
                        self._dispatch(message)
            except asyncio.CancelledError:
                return
            except Exception as err:
                _LOGGER.warning(
                    "Jackery MQTT session error: %s; reconnecting in %.0fs",
                    err,
                    self._reconnect_delay,
                )
            finally:
                self._client = None
                self._connected.clear()
                self._fail_pending(RuntimeError("MQTT session disconnected"))

            if not self._running:
                return
            try:
                await asyncio.sleep(self._reconnect_delay)
            except asyncio.CancelledError:
                return
            self._reconnect_delay = min(
                self._reconnect_delay * 2, self._MAX_RECONNECT_DELAY
            )

    def register_push_handler(self, device_sn: str, handler: callable) -> None:
        """Register a handler for unsolicited push messages from device_sn."""
        self._push_handlers[device_sn] = handler

    def _dispatch(self, message) -> None:
        """Route an incoming message to a pending future or a push handler."""
        try:
            data = json.loads(message.payload)
        except (json.JSONDecodeError, TypeError):
            return

        if (
            self._pending_future is not None
            and not self._pending_future.done()
            and self._pending_matcher is not None
            and self._pending_matcher(data)
        ):
            self._pending_future.set_result(data)
            return

        device_sn = data.get("deviceSn", "")
        handler = self._push_handlers.get(device_sn)
        if handler is not None:
            handler(data)
        else:
            _LOGGER.debug(
                "MQTT push: deviceSn=%s actionId=%s",
                device_sn,
                data.get("actionId"),
            )

    def _fail_pending(self, err: Exception) -> None:
        """Fail the pending future (no-op if none outstanding)."""
        if self._pending_future is not None and not self._pending_future.done():
            self._pending_future.set_exception(err)
        self._pending_matcher = None
        self._pending_future = None

    async def publish_and_wait(
        self,
        payload: dict,
        matcher: "callable",
        timeout: float = 10.0,
    ) -> dict:
        """Publish a command and await a matching response.

        Waits up to *timeout* seconds total: first for the session to connect
        (handles startup latency), then for a matching response after publish.
        """
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout

        if not self._connected.is_set():
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError("MQTT session not connected")
            try:
                async with asyncio.timeout(remaining):
                    await self._connected.wait()
            except TimeoutError:
                raise TimeoutError(
                    f"MQTT session did not connect within {timeout:.0f}s"
                ) from None

        async with self._operation_lock:
            if self._client is None or self._user_id is None:
                raise RuntimeError("MQTT session disconnected")

            loop = asyncio.get_running_loop()
            self._pending_future = loop.create_future()
            self._pending_matcher = matcher
            try:
                cmd_topic = f"hb/app/{self._user_id}/command"
                payload_str = json.dumps(payload, separators=(",", ":"))
                await self._client.publish(cmd_topic, payload_str, qos=1)

                remaining = deadline - loop.time()
                if remaining <= 0:
                    raise TimeoutError("MQTT operation timed out after publish")
                async with asyncio.timeout(remaining):
                    return await self._pending_future
            finally:
                self._pending_matcher = None
                self._pending_future = None


class JackeryAuthenticationError(Exception):
    """Exception to indicate an authentication error."""


class JackeryAPI:
    """A client to interact with the Jackery Cloud API."""

    def __init__(
        self, account: str, password: str, android_id: str = "abcd1234567890ef"
    ):
        """Initialize the API client."""
        self.account = account
        self.password = password
        self.android_id = android_id
        self.base_url = "https://iot.jackeryapp.com"
        self._token: Optional[str] = None
        self._token_expiry_time: float = (
            0  # We will assume a long expiry for simplicity
        )
        self._mqtt_user_id: Optional[str] = None
        self._mqtt_password_b64: Optional[str] = None
        self._mac_id: str = self._generate_udid()
        self._control_client = None
        self._control_client_lock = asyncio.Lock()
        self._control_write_lock = asyncio.Lock()
        self._login_lock = threading.Lock()
        self._last_login_time: float = 0
        self._mqtt_session: Optional[JackeryMqttSession] = None

    def _name_uuid_from_bytes_java(self, data: bytes) -> str:
        """Generate a version 3 UUID using an MD5 hash."""
        md5_digest = hashlib.md5(data).digest()
        u = uuid.UUID(bytes=md5_digest, version=3)
        return str(u).replace("-", "")

    def _generate_udid(self) -> str:
        """Generate a UDID."""
        if self.android_id and self.android_id != "9774d56d682e549c":
            return "2" + self._name_uuid_from_bytes_java(
                self.android_id.encode("utf-8")
            )
        else:
            random_uuid_str = str(uuid.uuid4()).replace("-", "")
            return "9" + random_uuid_str

    def _encrypt_with_aes(self, plain_text: str, aes_key: bytes) -> str:
        """Perform AES encryption."""
        cipher = AES.new(aes_key, AES.MODE_ECB)
        encrypted = cipher.encrypt(pad(plain_text.encode("utf-8"), AES.block_size))
        return base64.b64encode(encrypted).decode("utf-8")

    def _encrypt_with_rsa(self, data: bytes, public_key_b64: str) -> str:
        """Perform RSA encryption."""
        pub_key_pem = (
            f"-----BEGIN PUBLIC KEY-----\n{public_key_b64}\n-----END PUBLIC KEY-----"
        )
        pub_key = RSA.importKey(pub_key_pem)
        cipher = PKCS1_v1_5.new(pub_key)
        encrypted = cipher.encrypt(data)
        return base64.b64encode(encrypted).decode("utf-8")

    def login(self) -> bool:
        """Perform the login process and store the token."""
        with self._login_lock:
            # If another thread just logged in, reuse its credentials
            if time.monotonic() - self._last_login_time < 5 and self._token:
                _LOGGER.debug("Skipping login - another thread refreshed credentials %.1fs ago",
                              time.monotonic() - self._last_login_time)
                return True
            return self._login_inner()

    def _login_inner(self) -> bool:
        """Actual login implementation (must be called with _login_lock held)."""
        _LOGGER.info("Attempting to login to Jackery service")
        mac_id = self._generate_udid()
        login_bean = {
            "account": self.account,
            "loginType": 2,
            "macId": mac_id,
            "password": self.password,
            "phone": "",
            "registerAppId": "com.hbxn.jackery",
            "verificationCode": "",
        }

        public_key_b64 = "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCVmzgJy/4XolxPnkfu32YtJqYGFLYqf9/rnVgURJED+8J9J3Pccd6+9L97/+7COZE5OkejsgOkqeLNC9C3r5mhpE4zk/HStss7Q8/5DqkGD1annQ+eoICo3oi0dITZ0Qll56Dowb8lXi6WHViVDdih/oeUwVJY89uJNtTWrz7t7QIDAQAB"
        aes_key = b"1234567890123456"
        login_bean_json = json.dumps(login_bean, ensure_ascii=False)
        aes_encrypt_data = self._encrypt_with_aes(login_bean_json, aes_key)
        rsa_for_aes_key = self._encrypt_with_rsa(aes_key, public_key_b64)

        url = f"{self.base_url}/v1/auth/login"
        params = {"aesEncryptData": aes_encrypt_data, "rsaForAesKey": rsa_for_aes_key}
        headers = {
            "app_version": "1.0.5",
            "upload-incomplete": "?0",
            "sys_version": "17.2",
            "platform": "1",
            "upload-draft-interop-version": "3",
            "accept": "*/*",
            "accept-language": "en-US",
            "accept-encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "User-Agent": "DxPowerProject/1.0.5 (com.hb.jackery; build:2; iOS 17.2.0) Alamofire/5.8.0",
            "model": "iPad Pro (12.9-inch) (3rd generation)",
        }
        files = {"file": ("", b"", "")}

        try:
            response = requests.post(
                url, params=params, headers=headers, files=files, timeout=10
            )
            _LOGGER.debug("Login response status: %s", response.status_code)
            response.raise_for_status()
            data = response.json()
            _LOGGER.debug("Login response data: %s", _redact(data))

            if data.get("code") == 0 and "token" in data:
                self._token = data["token"]
                login_data = data.get("data", {})
                self._mqtt_user_id = str(login_data.get("userId", ""))
                self._mqtt_password_b64 = str(login_data.get("mqttPassWord", ""))
                self._last_login_time = time.monotonic()
                # Invalidate cached socketry client so next control use rebuilds
                # with fresh credentials rather than a stale token.
                self._control_client = None
                _LOGGER.info("Successfully logged in and obtained token.")
                return True
            else:
                error_msg = f"Login failed: {data.get('msg', 'Unknown error')} (code: {data.get('code')})"
                _LOGGER.error(error_msg)
                raise JackeryAuthenticationError(data.get("msg", "Login failed"))
        except requests.RequestException as e:
            _LOGGER.error("Login request failed: %s", e)
            raise JackeryAuthenticationError(f"Request failed: {e}") from e

    def _get_request(self, url_path: str, params: Optional[dict] = None) -> dict:
        """Make a GET request to the API, handling token expiry."""
        if not self._token:
            _LOGGER.info("No token found, logging in.")
            if not self.login():
                raise JackeryAuthenticationError("Unable to login to retrieve token.")

        headers = {
            "content-type": "application/json",
            "accept": "*/*",
            "app_version": "1.0.5",
            "sys_version": "17.2",
            "accept-encoding": "br;q=1.0, gzip;q=0.9, deflate;q=0.8",
            "accept-language": "en-US",
            "platform": "1",
            "user-agent": "DxPowerProject/1.0.5 (com.hb.jackery; build:2; iOS 17.2.0) Alamofire/5.8.0",
            "model": "iPad Pro (12.9-inch) (3rd generation)",
            "token": self._token,
        }
        full_url = f"{self.base_url}{url_path}"
        _LOGGER.debug("Making API request to: %s", full_url)

        try:
            response = requests.get(
                full_url, headers=headers, params=params, timeout=10
            )
            _LOGGER.debug("API response status: %s", response.status_code)
            response.raise_for_status()
            data = response.json()
            _LOGGER.debug("API response data: %s", _redact(data))

            # 10402 = token expired; 10403 = session displaced by another login
            if data.get("code") in (10402, 10403):
                _LOGGER.info("Re-logging in (code=%s)...", data.get("code"))
                if not self.login():
                    raise JackeryAuthenticationError(
                        "Failed to re-login after session invalidated."
                    )
                # Retry the request with the new token
                headers["token"] = self._token
                response = requests.get(
                    full_url, headers=headers, params=params, timeout=10
                )
                response.raise_for_status()
                data = response.json()

            if data.get("code") != 0:
                error_msg = f"API Error: {data.get('msg', 'Unknown error')} (code: {data.get('code')})"
                _LOGGER.error(error_msg)
                raise Exception(error_msg)

            return data

        except requests.RequestException as e:
            _LOGGER.error("API request failed: %s", e)
            raise

    def get_device_list(self) -> dict:
        """Get the list of devices."""
        _LOGGER.info("Attempting to fetch device list from Jackery API")
        try:
            result = self._get_request("/v1/device/bind/list")
            _LOGGER.info("Successfully retrieved device list")
            return result
        except Exception as e:
            _LOGGER.error("Failed to get device list: %s", str(e))
            raise

    def get_device_detail(self, device_id: str) -> dict:
        """Get detailed information for a specified device."""
        return self._get_request("/v1/device/property", params={"deviceId": device_id})

    async def _async_get_control_client(self):
        """Get an authenticated Socketry client for device control."""
        async with self._control_client_lock:
            if self._control_client is not None:
                return self._control_client

            if socketry is None:
                raise RuntimeError("socketry is not installed")
            if not self._mqtt_user_id or not self._mqtt_password_b64 or not self._token:
                raise RuntimeError("MQTT credentials not available - call login() first")

            # Build from existing HA credentials to avoid a new HTTP login that
            # would rotate the auth token. Omitting email/password prevents
            # socketry from ever calling _http_login internally.
            creds = {
                "userId": self._mqtt_user_id,
                "mqttPassWord": self._mqtt_password_b64,
                "token": self._token,
                "macId": self._mac_id,
                "deviceSn": "",
                "deviceId": "",
                "deviceName": "",
                "devices": [],
            }
            client = None
            try:
                client = socketry.Client(creds)
                await client.fetch_devices()
            except asyncio.CancelledError:
                await self._async_close_control_client(client)
                raise
            except Exception:
                await self._async_close_control_client(client)
                raise
            self._control_client = client
            return client

    async def start_mqtt_session(self) -> None:
        """Start the persistent MQTT session (no-op if dependencies are missing)."""
        if aiomqtt is None or _socketry_mqtt_params is None:
            return
        if self._mqtt_session is not None:
            return
        self._mqtt_session = JackeryMqttSession(self)
        await self._mqtt_session.start()

    async def stop_mqtt_session(self) -> None:
        """Stop the persistent MQTT session."""
        if self._mqtt_session is not None:
            await self._mqtt_session.stop()
            self._mqtt_session = None

    def register_push_handler(self, device_sn: str, handler: callable) -> None:
        """Register a handler for unsolicited MQTT push messages from device_sn."""
        if self._mqtt_session is not None:
            self._mqtt_session.register_push_handler(device_sn, handler)

    async def async_close(self) -> None:
        """Stop the MQTT session and release the cached Socketry control client."""
        await self.stop_mqtt_session()
        async with self._control_write_lock:
            await self._async_reset_control_client()

    async def _async_reset_control_client(self, client=None) -> None:
        """Drop the cached control client and close the discarded instance."""
        async with self._control_client_lock:
            client_to_close = self._control_client if client is None else client
            if client is None:
                self._control_client = None
            elif self._control_client is client:
                self._control_client = None

        await self._async_close_control_client(client_to_close)

    async def _async_close_control_client(self, client) -> None:
        """Best-effort close a discarded Socketry control client."""
        if client is None:
            return

        for method_name in ("stop", "disconnect", "close"):
            method = getattr(client, method_name, None)
            if method is None:
                continue

            try:
                result = method()
                if inspect.isawaitable(result):
                    await result
                break  # first successful close wins; don't try remaining methods
            except asyncio.CancelledError:
                raise
            except Exception as err:  # pragma: no cover - defensive cleanup
                _LOGGER.debug(
                    "Failed to %s discarded Socketry control client: %s",
                    method_name,
                    err,
                )

    async def async_set_device_property(
        self,
        device_id: str,
        device_sn: str,
        property_slug: str,
        value: str | int,
    ) -> None:
        """Set a portable device property via the persistent MQTT session.

        Routes all writes through JackeryMqttSession so that controls and the
        push/poll subscription share one MQTT connection (client ID
        ``{userId}@APP``).  Using a separate socketry control connection with the
        same client ID would kick out the persistent session, causing the Jackery
        backend to treat it as a competing app login and invalidate the REST
        token (error 10403).
        """
        if aiomqtt is None:
            raise RuntimeError("aiomqtt is not installed")
        if self._mqtt_session is None:
            raise RuntimeError("MQTT session not started - call start_mqtt_session() first")

        # Look up action_id and prop_key from our own control spec registry first
        # (avoids depending on socketry's internal property definitions at write time).
        from .protocol import CONTROL_SPECS_BY_SLUG
        spec = CONTROL_SPECS_BY_SLUG.get(property_slug)
        if spec is not None and spec.action_id is not None:
            action_id = spec.action_id
            prop_key = spec.prop_key
        elif socketry is not None:
            # Fallback: use socketry to resolve unknown slugs (e.g. future device props).
            from socketry.properties import resolve as _socketry_resolve
            setting = _socketry_resolve(property_slug)
            if setting is None or setting.action_id is None:
                raise KeyError(f"Unknown or read-only property slug: {property_slug!r}")
            action_id = setting.action_id
            prop_key = setting.prop_key
        else:
            raise KeyError(f"Cannot resolve property slug without socketry: {property_slug!r}")

        body = {prop_key: int(value)}
        await self.async_send_device_command(device_id, device_sn, action_id, body)

    def _build_mqtt_params(self) -> tuple[dict, str]:
        """Build aiomqtt connection params from REST API login credentials.

        Returns ``(params_dict, user_id)``.
        """
        if _socketry_mqtt_params is None:
            raise RuntimeError("socketry is not installed")
        if not self._mqtt_user_id or not self._mqtt_password_b64:
            raise RuntimeError("MQTT credentials not available - call login() first")
        creds = {
            "userId": self._mqtt_user_id,
            "mqttPassWord": self._mqtt_password_b64,
            "macId": self._mac_id,
        }
        return _socketry_mqtt_params(creds), self._mqtt_user_id

    async def async_send_device_command(
        self,
        device_id: str,
        device_sn: str,
        action_id: int,
        body: dict,
        message_type: str = "DevicePropertyChange",
        ack_cmd: int | None = None,
    ) -> dict | None:
        """Send a raw MQTT command via the persistent Transfer Switch session.

        Returns the matched response, or None if there was none. Set ``ack_cmd``
        when the actionId is shared with periodic pushes (Transfer Switch actionId 1).
        """
        if aiomqtt is None:
            raise RuntimeError("aiomqtt is not installed")
        if self._mqtt_session is None:
            raise RuntimeError("MQTT session not started - call start_mqtt_session() first")

        ts = int(time.time() * 1000)
        payload = {
            "deviceSn": device_sn,
            "id": ts,
            "version": 0,
            "messageType": message_type,
            "actionId": action_id,
            "timestamp": ts,
            "body": body,
        }
        _LOGGER.info("MQTT publish: actionId=%d body=%s", action_id, body)

        # Accept a response echoing the same actionId from this device.
        # ack_cmd also distinguishes the reply from periodic pushes sharing the actionId.
        def _match(data: dict) -> bool:
            if data.get("deviceSn") != device_sn or data.get("actionId") != action_id:
                return False
            if ack_cmd is None:
                return True
            resp_body = data.get("body")
            return isinstance(resp_body, dict) and resp_body.get("cmd") == ack_cmd

        try:
            result = await self._mqtt_session.publish_and_wait(payload, _match, timeout=5.0)
            _LOGGER.info(
                "MQTT response: messageType=%s actionId=%s body=%s",
                result.get("messageType"),
                result.get("actionId"),
                result.get("body"),
            )
            return result
        except TimeoutError:
            _LOGGER.warning("No MQTT response within 5s for actionId=%d", action_id)
        except Exception:
            _LOGGER.exception("MQTT command failed for actionId=%d device=%s", action_id, device_sn)
        return None

    async def async_set_device_dp(
        self,
        device_id: str,
        device_sn: str,
        dp_id: str | int,
        value: str | int | bool,
    ) -> None:
        """Set a raw device DP through the existing control channel."""
        await self.async_set_device_property(
            device_id,
            device_sn,
            str(dp_id),
            value,
        )

    @staticmethod
    def _resolve_control_device(client, device_id: str, device_sn: str):
        """Resolve a controllable device from the cached Socketry device list."""
        for device in client.devices:
            if str(device.get("devId", "")) == str(device_id):
                return client.device(str(device["devSn"]))
            if device_sn and str(device.get("devSn", "")) == str(device_sn):
                return client.device(str(device["devSn"]))

        raise KeyError(
            f"Unable to resolve Jackery device for control (device_id={device_id}, "
            f"device_sn={device_sn})."
        )

    async def async_query_transfer_switch_plans(
        self,
        device_sn: str,
    ) -> list[dict]:
        """Query charge/discharge plans from Transfer Switch via persistent MQTT session."""
        if aiomqtt is None:
            raise RuntimeError("aiomqtt is not installed")
        if self._mqtt_session is None:
            raise RuntimeError("MQTT session not started - call start_mqtt_session() first")

        ts = int(time.time() * 1000)
        payload = {
            "deviceSn": device_sn,
            "id": ts,
            "version": 0,
            "messageType": "QueryElectricityStrategy",
            "actionId": 12,
            "timestamp": ts,
            "body": {"cmd": 15},
        }

        def _match(data: dict) -> bool:
            return (
                data.get("deviceSn") == device_sn
                and isinstance(data.get("body"), dict)
                and "cds" in data["body"]
            )

        try:
            result = await self._mqtt_session.publish_and_wait(payload, _match, timeout=10.0)
            return result["body"]["cds"]
        except TimeoutError:
            _LOGGER.warning("Timeout waiting for plan query response from %s", device_sn)
        except Exception:
            _LOGGER.exception("Failed to query plans for %s", device_sn)
        return []

    async def async_update_transfer_switch_plan(
        self,
        device_id: str,
        device_sn: str,
        plan: dict,
    ) -> None:
        """Update an existing charge/discharge plan on the Transfer Switch."""
        await self.async_send_device_command(
            device_id,
            device_sn,
            14,  # actionId for UpdateElectricityStrategy
            {"cmd": 17, **plan},
            message_type="UpdateElectricityStrategy",
        )

    async def async_create_transfer_switch_plan(
        self,
        device_id: str,
        device_sn: str,
        plan: dict,
    ) -> None:
        """Create a new charge/discharge plan on the Transfer Switch."""
        await self.async_send_device_command(
            device_id,
            device_sn,
            13,  # actionId for InsertElectricityStrategy
            {"cmd": 16, **plan},
            message_type="InsertElectricityStrategy",
        )

    async def async_delete_transfer_switch_plan(
        self,
        device_id: str,
        device_sn: str,
        pid: str,
    ) -> None:
        """Delete a charge/discharge plan on the Transfer Switch."""
        await self.async_send_device_command(
            device_id,
            device_sn,
            15,  # actionId for DeleteElectricityStrategy
            {"cmd": 18, "pid": pid},
            message_type="DeleteElectricityStrategy",
        )

    async def async_query_transfer_switch_circuits(
        self,
        device_sn: str,
    ) -> list[dict]:
        """Query circuit properties from Transfer Switch via persistent MQTT session."""
        if aiomqtt is None:
            raise RuntimeError("aiomqtt is not installed")
        if self._mqtt_session is None:
            raise RuntimeError("MQTT session not started - call start_mqtt_session() first")

        ts = int(time.time() * 1000)
        payload = {
            "deviceSn": device_sn,
            "id": ts,
            "version": 0,
            "messageType": "QueryCircuitProperty",
            "actionId": 7,
            "timestamp": ts,
            "body": {"cmd": 10},
        }

        def _match(data: dict) -> bool:
            # Only accept actionId=7 (full QueryCircuitProperty response).
            # actionId=1 are unsolicited partial power-only pushes - ignore them.
            return (
                data.get("deviceSn") == device_sn
                and data.get("actionId") == 7
                and isinstance(data.get("body"), dict)
                and "cir" in data["body"]
            )

        try:
            result = await self._mqtt_session.publish_and_wait(payload, _match, timeout=10.0)
            return result["body"]["cir"]
        except TimeoutError:
            _LOGGER.warning("Timeout waiting for circuit query response from %s", device_sn)
        except Exception:
            _LOGGER.exception("Failed to query circuits for %s", device_sn)
        return []

    async def async_set_circuit_switch(
        self,
        device_id: str,
        device_sn: str,
        idx: int,
        on: bool,
    ) -> None:
        """Toggle a circuit on/off on the Transfer Switch."""
        await self.async_send_device_command(
            device_id,
            device_sn,
            9,  # actionId for circuit switch
            {"cmd": 12, "idx": idx, "sw": 1 if on else 0},
        )
