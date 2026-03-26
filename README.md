> I have a full time job and can't respond to issues, but I'm open to contributions! If you submit a reasonable pull request, I will review, respond, test, and merge if it looks good. Thank you for understanding!

# Jackery Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![maintainer](https://img.shields.io/badge/maintainer-%40theak-blue.svg)](https://github.com/theak)
[![version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/theak/jackery-homeassistant)

Custom Home Assistant integration for monitoring and controlling Jackery portable power stations. This integration provides real-time sensor data plus model-aware control entities for supported Jackery devices.

## Features

- 🔋 **Battery Monitoring**: Track remaining battery percentage and temperature
- ⚡ **Power Monitoring**: Monitor input/output power in watts
- ⏱️ **Time Tracking**: View time to full charge and remaining output time
- 🔌 **Output Control**: Switches for supported AC, DC, USB, and car outputs
- ⚙️ **Device Controls**: Select and number entities for light mode, charge speed, battery protection, screen timeout, and more
- 🧠 **Model-Aware Entities**: Only shows entities that the specific Jackery model actually reports
- 📡 **MQTT Control Path**: Uses Jackery's device control channel for supported writable settings

## Supported Sensors

### Regular Sensors

| Sensor                | Description                   | Unit     |
| --------------------- | ----------------------------- | -------- |
| Remaining Battery     | Current battery level         | %        |
| Battery Temperature   | Battery temperature           | °C       |
| Output Power          | Current power output          | W        |
| Input Power           | Current power input           | W        |
| AC Input Power        | AC power input                | W        |
| Car Input Power       | Car charging input            | W        |
| Time to Full          | Estimated time to full charge | hours    |
| Remaining Output Time | Estimated remaining runtime   | hours    |
| AC Output Voltage     | AC output voltage             | V        |
| AC Output Frequency   | AC output frequency           | Hz       |
| Error Code            | Device error code             | n/a      |
| Last Updated          | Timestamp of last data update | ISO 8601 |

### Switches and Status

Supported models expose different combinations of controllable entities. Examples include:

| Entity Type | Examples |
| ----------- | -------- |
| Switches | AC Output, DC Output, USB Output, DC Car Output, Super Fast Charge, UPS Mode |
| Selects | Light Mode, Charge Speed, Battery Protection |
| Numbers | Auto Shutdown, Energy Saving, Screen Timeout |
| Binary Sensors | Temperature Alarm, Power Alarm, Wireless Charging |

**Note:** Different Jackery device models report different property sets. For example, some units expose a combined `odc` DC switch while others expose separate `odcc` and `odcu` switches for car and USB outputs. Unsupported controls are not created for devices that do not report those properties.

## Installation

### Option 1: HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS
3. Search for "Jackery" in the integrations section
4. Install version `1.1.0` or newer and restart Home Assistant to load the integration code

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
- Each device will have its own set of supported sensors, switches, selects, and number entities

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
      entity_id: switch.jackery_device_ac_output
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

2. **HACS rejects version 1.0.1**
   - Install version `1.1.0` or newer
   - Version `1.0.1` was tagged before `hacs.json` was moved to the repository root, which newer HACS versions require

3. **No Devices Found**
   - Make sure your Jackery device is connected to the internet
   - Verify the device is registered to your account

4. **Sensors Not Updating**
   - Check the Home Assistant logs for errors
   - Verify your device has internet connectivity

5. **Entities missing or extra entities are still shown after upgrading**
   - Reload the Jackery config entry or restart Home Assistant after upgrading
   - The integration creates entities based on the live property set reported by each device model

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

## Dependencies

- `requests>=2.31.0`
- `pycryptodomex>=3.19.0`
- `socketry>=0.2.3`

## Contributing

Pull Requests are encouraged and welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based heavily on code from https://qiita.com/Hsky16/items/c163137265a87186ac39
- Thanks to the Home Assistant community for the excellent framework
- Special thanks to all contributors and users who provide feedback

---

**Note**: This is a community-driven integration and is not officially affiliated with Jackery. Use at your own risk.
