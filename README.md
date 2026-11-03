> This is a community-maintained project. Issue responses may be slow, but pull requests are welcome! Reasonable PRs will be reviewed, tested, and merged.

> **Note:** This integration targets the **Jackery** app backend (used by portable stations like the Explorer series and Smart Transfer Switch). If your device is managed by the **Jackery Home** app (e.g. HomePower 2000 Ultra, SolarVault), that app uses a different API; see [iLLixM/jackery_home_cloud-ha](https://github.com/iLLixM/jackery_home_cloud-ha) for a community integration targeting that backend.

# Jackery Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![maintainer](https://img.shields.io/badge/maintainer-%40theak-blue.svg)](https://github.com/theak)
[![version](https://img.shields.io/badge/version-1.3.1-blue.svg)](https://github.com/theak/jackery-homeassistant)

Custom Home Assistant integration for monitoring and controlling Jackery portable power stations and the Smart Transfer Switch. Provides real-time sensors, writable controls, and automation services.

## Features

- Battery, power, and time-remaining sensors for portable power stations
- Writable switches, selects, and number entities for supported device settings
- Charging plan support for Jackery Plus portable models
- Smart Transfer Switch: grid/station toggle, UPS mode, working mode selection, circuit control, fault diagnostics, and scheduled charge/discharge plan management
- Per-circuit power monitoring with automatic split-phase pair combining
- Custom Lovelace cards for plan and circuit management

For the full entity reference, see the [Wiki](../../wiki).

## Installation

### HACS (Recommended)

1. Install [HACS](https://hacs.xyz/) if you have not already.
2. Add this repository as a custom repository in HACS.
3. Search for "Jackery" in the integrations section and click Download.
4. Restart Home Assistant.

HACS installs from published GitHub releases. To get unreleased fixes, HACS can also install the repository's default branch directly.

### Manual

1. Download or clone this repository.
2. Copy the `jackery` folder to your `config/custom_components/` directory.
3. Restart Home Assistant.

## Configuration

1. Go to **Settings** > **Devices and Services** > **Add Integration**.
2. Search for "Jackery" and select it.
3. Enter your Jackery account email and password.
4. Click **Submit**.

The integration will discover your devices and create all supported entities automatically.

## Requirements

- Home Assistant 2023.8.0 or newer
- Python 3.10 or newer

**Dependencies:**
- `requests>=2.31.0`
- `pycryptodomex>=3.19.0`
- `socketry>=0.2.4`

## Wiki

Full documentation is available in the [Wiki](../../wiki):

| Page | Contents |
|------|----------|
| [Charging Plans](../../wiki/Charging-Plans) | Scheduled charge/discharge plan details and protocol |
| [Controls](../../wiki/Controls) | Switches, selects, numbers, and text entities |
| [Device Availability](../../wiki/Device-Availability) | Which entities are created for which devices |
| [Example Automations](../../wiki/Example-Automations) | Sample automations for common use cases |
| [Lovelace Cards](../../wiki/Lovelace-Cards) | Custom card setup and features |
| [Portable Devices](../../wiki/Portable-Devices) | Portable station features, charging behavior, and quirks |
| [Properties](../../wiki/Properties) | Raw device property key reference |
| [Sensors](../../wiki/Sensors) | All sensor and binary sensor reference tables |
| [Services](../../wiki/Services) | HA services for Transfer Switch plan management |
| [Supported Devices](../../wiki/Supported-Devices) | Known supported hardware and compatibility notes |
| [Transfer Switch](../../wiki/Transfer-Switch) | Smart Transfer Switch working modes, circuits, fault diagnostics |
| [Troubleshooting](../../wiki/Troubleshooting) | Common issues and debug logging |

## Lovelace Cards

Custom Lovelace cards for the Transfer Switch are available in a separate repository:

**[jackery-lovelace-cards](https://github.com/turmacar/jackery-lovelace-cards)**

See [Lovelace Cards](../../wiki/Lovelace-Cards) in the wiki for details on each card.

## Contributing

Pull requests are encouraged and welcome! For major changes, open an issue first to discuss what you would like to change.

When changing `custom_components/jackery/manifest.json` version metadata, push the matching semantic version tag so HACS can install that version directly.

## License

MIT - see [LICENSE](LICENSE).

## Acknowledgments

- Based heavily on code from https://qiita.com/Hsky16/items/c163137265a87186ac39
- Thanks to the Home Assistant community for the excellent framework
- Special thanks to all contributors and users who provide feedback

---

**Note:** This is a community-driven integration and is not officially affiliated with Jackery. Use at your own risk.
