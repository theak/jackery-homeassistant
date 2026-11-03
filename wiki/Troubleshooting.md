# Troubleshooting

## Debug Logging

To enable verbose logging for the integration, add the following to your `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.jackery: debug
```

Logs can be viewed under **Settings** > **System** > **Logs**.

Credentials and device secrets (`token`, `mqttPassWord`, `deviceSecret`, `randomSalt`) are masked in the debug output.

## Common Issues

### Authentication Failed

- Verify your Jackery account credentials.
- Ensure the account is active and not locked.
- **EU accounts are not currently supported.** If your account was registered through the EU region, the integration will not be able to authenticate.

### No Devices Found

- Confirm your device is connected to the internet and powered on.
- Verify the device is registered to the same account used during integration setup.

### Sensors Not Updating

- Check the Home Assistant logs for errors related to `custom_components.jackery`.
- Verify the device has a stable internet connection.
- If the device's entities show unavailable, see [Device Offline From the Jackery Cloud](#device-offline-from-the-jackery-cloud).

### Device Offline From the Jackery Cloud

The Jackery cloud keeps returning a device's last known values after the device loses its internet connection. The integration reads the cloud's online status, so an offline device shows **unavailable** and its **Cloud Connection** sensor turns off. After 10 minutes a Repair issue appears under **Settings** > **System** > **Repairs**.

Some stations (observed on the Explorer 5000 Plus and Explorer 300 Plus) do not reconnect by themselves after an internet outage. To restore them, re-enable Wi-Fi on the device and re-add it in the Jackery app. The Smart Transfer Switch reconnects on its own. No fault codes are reported while offline.

The Repair issue clears on the next poll after the device is back online. For a phone notification as well, see [Example Automations](Example-Automations#device-offline-notification).

### Plan or Circuit Entities Missing

- Plan and circuit entities are only created for the Smart Transfer Switch.
- Both are queried on startup via the persistent MQTT connection. If the initial query has not yet completed, entities may appear within a few minutes of setup.
- If entities are still missing after several minutes, check the logs for MQTT connection errors.

### AC1/AC2 Pack Sensors Not Appearing

Add-on battery pack sensors can take 24 hours or more to appear after a pack is first connected. The device registers the pack gradually over time.

### Charging Plan Time / Repeat Unavailable

These entities become unavailable if the device reports DP 108 with a missing or malformed payload, or when the device is connected to a Smart Transfer Switch. Check device connectivity and wait for the next successful poll.

---

For example automations, see [Example Automations](Example-Automations).
