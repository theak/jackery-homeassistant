> While this custom integration currently works as of January 2026, I unfortunately have a full time job and can't respond to all issues. That being said, if you submit a reasonable pull request, I will review, respond, and merge it in if it looks good. Thank you for your understanding!

# Jackery Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![maintainer](https://img.shields.io/badge/maintainer-%40theak-blue.svg)](https://github.com/theak)
[![version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/theak/jackery-homeassistant)

Custom Home Assistant integration for monitoring Jackery portable power stations. This integration provides real-time sensor data for your Jackery devices including battery status, power output, temperature, and more.

## Features

- 🔋 **Battery Monitoring**: Track remaining battery percentage and temperature
- ⚡ **Power Monitoring**: Monitor input/output power in watts
- ⏱️ **Time Tracking**: View time to full charge and remaining output time
- 🔌 **Output Status**: Binary sensors for AC, DC car, and USB output status
- 📊 **Real-time Updates**: Automatic polling every 60 seconds
- 🔐 **Secure Authentication**: Uses your Jackery account credentials

## Supported Sensors

### Regular Sensors

| Sensor                | Description                   | Unit     |
| --------------------- | ----------------------------- | -------- |
| Remaining Battery     | Current battery level         | %        |
| Battery Temperature   | Battery temperature           | °C       |
| Output Power          | Current power output          | W        |
| Input Power           | Current power input           | W        |
| AC Input Power        | AC power input                | W        |
| Time to Full          | Estimated time to full charge | hours    |
| Remaining Output Time | Estimated remaining runtime   | hours    |
| AC Output Voltage     | AC output voltage             | V        |
| Last Updated          | Timestamp of last data update | ISO 8601 |

### Binary Sensors (ON/OFF)

| Sensor        | Description               |
| ------------- | ------------------------- |
| AC Output     | AC output status          |
| DC Output     | DC output status          |
| DC Car Output | DC car port output status |
| USB Output    | USB output status         |

**Note:** Different Jackery device models may report different combinations of DC output sensors. Early exploration suggests some models use a combined `odc` parameter while others use separate `odcc` and `odcu` parameters.

## Installation

### Option 1: HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS
3. Search for "Jackery" in the integrations section
4. Click "Download" and restart Home Assistant

### Option 2: Manual Installation

1. Download or clone this repository
2. Copy the `jackery` folder to your `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Jackery" and select it
4. Enter your Jackery account credentials:
   - **Username**: Your Jackery account email/username
   - **Password**: Your Jackery account password
5. Click **Submit**

The integration will automatically discover your Jackery devices and create sensors for each one.

## Usage

Once configured, you'll find your Jackery devices and their sensors in:

- **Settings** → **Devices & Services** → **Entities**
- Each device will have its own set of sensors

You can use these sensors in:

- **Dashboards**: Create custom dashboards to monitor your power station
- **Automations**: Set up automations based on battery level, power status, etc.
- **Templates**: Use sensor values in templates for custom calculations

### Example Automations

```yaml
# Low battery alert
automation:
  - alias: "Low Battery Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.jackery_device_remaining_battery
      below: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Jackery battery is low: {{ states('sensor.jackery_device_remaining_battery') }}%"

  # AC output turned on notification
  - alias: "Jackery AC Output On"
    trigger:
      platform: state
      entity_id: binary_sensor.jackery_device_ac_output
      to: "on"
    action:
      - service: notify.mobile_app
        data:
          message: "Jackery AC output has been turned on"
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify your Jackery account credentials
   - Ensure your account is active and not locked

2. **No Devices Found**
   - Make sure your Jackery device is connected to the internet
   - Verify the device is registered to your account

3. **Sensors Not Updating**
   - Check the Home Assistant logs for errors
   - Verify your device has internet connectivity

### Logs

To enable debug logging, add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.jackery: debug
```

## Requirements

- Home Assistant 2023.8.0 or newer
- Python 3.10 or newer
- Internet connection for device communication

## Dependencies

- `requests>=2.31.0`
- `pycryptodomex>=3.19.0`

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based heavily on code from https://qiita.com/Hsky16/items/c163137265a87186ac39
- Thanks to the Home Assistant community for the excellent framework
- Special thanks to all contributors and users who provide feedback

---

**Note**: This is a community-driven integration and is not officially affiliated with Jackery. Use at your own risk.
