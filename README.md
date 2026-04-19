> I have a full time job and can't respond to issues, but I'm open to contributions! If you submit a reasonable pull request, I will review, respond, test, and merge if it looks good. Thank you for understanding!

> **Known issue:** This integration currently does not support accounts registered in the EU.

# Jackery Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![maintainer](https://img.shields.io/badge/maintainer-%40theak-blue.svg)](https://github.com/theak)
[![version](https://img.shields.io/badge/version-1.0.5-blue.svg)](https://github.com/theak/jackery-homeassistant)

Custom Home Assistant integration for monitoring and controlling Jackery portable power stations. This integration provides real-time sensor data for your Jackery devices along with writable controls for supported settings and charging plans on supported Jackery Plus models.

## Features

- 🔋 **Battery Monitoring**: Track remaining battery percentage, battery temperature, and battery status
- ⚡ **Power Monitoring**: Monitor total input, AC input, DC input, output power, AC output voltage, and AC output frequency
- ⏱️ **Time Tracking**: View time to full charge, remaining output time, and the last successful refresh timestamp
- 🔌 **Output Status**: Binary sensors for AC, DC, DC car, and USB output status where supported by the device
- 🎛️ **Device Controls**: Writable switches, selects, and number entities for supported Jackery settings
- 📅 **Charging Plans**: Charging-plan switch, time window, and repeat schedule for supported Jackery Plus devices

## Supported Sensors

### Regular Sensors

| Sensor                     | Description                                 | Unit     |
| -------------------------- | ------------------------------------------- | -------- |
| Remaining Battery          | Current battery level                       | %        |
| Battery Temperature        | Battery temperature                         | °C       |
| Battery Status             | Idle, Charging, Discharging, or Fault       | text     |
| Output Power               | Current power output                        | W        |
| Total Input Power          | Current total power input                   | W        |
| AC Input Power             | Current AC input power                      | W        |
| DC Input Power             | Current DC/car input power                  | W        |
| Time to Full               | Estimated time to full charge               | hours    |
| Remaining Output Time      | Estimated remaining runtime                 | hours    |
| AC Output Voltage          | Current AC output voltage                   | V        |
| AC Output Frequency        | Current AC output frequency                 | Hz       |
| Error Code                 | Reported device error code                  | integer  |
| Parallel Modules Connected | Reported external module count, if present  | integer  |
| Last Updated               | Timestamp of last successful data refresh   | ISO 8601 |

### Binary Sensors (ON/OFF)

| Sensor            | Description                       |
| ----------------- | --------------------------------- |
| AC Output         | AC output status                  |
| DC Output         | Combined DC output status         |
| DC Car Output     | DC car port output status         |
| USB Output        | USB output status                 |
| Temperature Alarm | Device temperature alarm status   |
| Power Alarm       | Device power/protection alarm     |

**Note:** Different Jackery device models may report different combinations of DC output sensors. Some models use a combined `odc` parameter while others use separate `odcc` and `odcu` parameters. The integration hides the combined DC entity when split USB/car output keys are available.

## Supported Controls

The integration creates writable entities only when the corresponding properties are reported by the device.

### Switches

| Entity              | Description                              |
| ------------------- | ---------------------------------------- |
| AC Output           | Toggle AC output                         |
| DC Output           | Toggle combined DC output                |
| DC Car Output       | Toggle DC car output                     |
| USB Output          | Toggle USB output                        |
| Super Fast Charge   | Toggle super fast charge mode            |
| Charging Plan       | Enable or disable charging plans         |

### Selects

| Entity                | Options                        |
| --------------------- | ------------------------------ |
| Light Mode            | `off`, `low`, `high`, `sos`    |
| Charge Speed          | `fast`, `mute`                 |
| Battery Protection    | `full`, `eco`                  |
| Charging Plan Repeat  | `Everyday`, `Weekdays`, `Weekends`, `Once` |

### Numbers

| Entity           | Description                     | Unit    |
| ---------------- | ------------------------------- | ------- |
| Auto Shutdown    | Auto shutdown delay             | minutes |
| Energy Saving    | Energy saving timer             | minutes |
| Screen Timeout   | Screen timeout delay            | minutes |

### Text

| Entity              | Description                                  | Format         |
| ------------------- | -------------------------------------------- | -------------- |
| Charging Plan Time  | Charging plan time window for supported devices | `HH:mm-HH:mm` |

## Device-Specific Availability

- Entities are created only when the Jackery API reports the underlying key for that device.
- `Charging Plan` appears when the device reports DP `107`.
- `Charging Plan Time` and `Charging Plan Repeat` appear when the device reports DP `108`.
- Devices that split DC control into `odcu` and `odcc` will not show the combined `DC Output` entity.
- `Parallel Modules Connected` appears only on devices that expose `pmb`.
- `Charging Plan Time` and `Charging Plan Repeat` become unavailable if the reported DP `108` payload is missing or malformed.

## Installation

### Option 1: HACS (Recommended)

1. Make sure you have [HACS](https://hacs.xyz/) installed
2. Add this repository as a custom repository in HACS
3. Search for "Jackery" in the integrations section
4. Click "Download" and restart Home Assistant

HACS installs published version tags from GitHub releases. This repository now publishes a matching GitHub release automatically whenever a semantic version tag is pushed.

If you need fixes that have not been published as a new GitHub release yet, HACS can also install the repository's default branch. This keeps branch installs available even while the latest published release remains `1.0.5`.

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

The integration will automatically discover your Jackery devices and create the supported entities for each one.

## Usage

Once configured, you'll find your Jackery devices and their entities in:

- **Settings** → **Devices & Services** → **Entities**
- Each device will have its own set of supported entities

You can use these entities in:

- **Dashboards**: Create custom dashboards to monitor your power station
- **Automations**: Set up automations based on battery level, power status, alarms, or control states
- **Templates**: Use sensor values in templates for custom calculations
- **Controls**: Change supported Jackery settings directly from Home Assistant

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

## Dependencies

- `requests>=2.31.0`
- `pycryptodomex>=3.19.0`
- `socketry>=0.2.4`

## Contributing

Pull Requests are encouraged and welcome! For major changes, please open an issue first to discuss what you would like to change.

When changing `custom_components/jackery/manifest.json` version metadata, push the matching semantic version tag so HACS can install that version directly.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based heavily on code from https://qiita.com/Hsky16/items/c163137265a87186ac39
- Thanks to the Home Assistant community for the excellent framework
- Special thanks to all contributors and users who provide feedback

---

**Note**: This is a community-driven integration and is not officially affiliated with Jackery. Use at your own risk.
