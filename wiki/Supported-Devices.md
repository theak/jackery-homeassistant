# Supported Devices

The integration supports any Jackery device that authenticates through the Jackery cloud API and uses the MQTT-based property protocol. The devices below have been tested. Other Jackery Plus series models may work but have not been verified.

If you have a device not listed here, or one marked as Community Testing, please open an issue or pull request with your findings.

## Device List

| Device | Model Number | Model Code | Status |
|--------|-------------|------------|--------|
| Explorer 300 Plus | HTE095300A | 4 | Supported |
| Explorer 1000 Plus | HTE287500A | 6 | Testing |
| Explorer 5000 Plus | HTE1195000A | 13 | Supported |
| Smart Transfer Switch (JA-TS02A) | HTO785A | 2001 | Supported |

## Status Definitions

**Supported** - Verified working. Core sensors and controls function correctly. At least some quirks are documented.

**Testing** - There are open questions or known issues with specific entities.

## EU Accounts

Accounts registered in the EU region are not currently supported. Authentication will fail for EU-registered accounts regardless of device model.

## Contributing Device Data

To help add or verify support for a device, an API response dump from the device is the most useful contribution. See the [Contributing](../CONTRIBUTING.md) guide (if available) or open a GitHub issue.
