"""API client for Jackery cloud services."""

import base64
import hashlib
import json
import logging
import uuid
from typing import Optional

import requests
from Cryptodome.Cipher import AES, PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from Cryptodome.Util.Padding import pad

_LOGGER = logging.getLogger(__name__)


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
            _LOGGER.debug("Login response data: %s", data)

            if data.get("code") == 0 and "token" in data:
                self._token = data["token"]
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
            _LOGGER.debug("API response data: %s", data)

            # Check for expired token (code=10402)
            if data.get("code") == 10402:
                _LOGGER.info("Token expired. Re-logging in...")
                if not self.login():
                    raise JackeryAuthenticationError(
                        "Failed to re-login after token expired."
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
