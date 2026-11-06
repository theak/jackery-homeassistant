# Sensors

All sensor entities created by the integration. Entities are created only when the Jackery API reports the underlying property for that device. Transfer Switch-only sensors are labeled accordingly.

See [Device Availability](Device-Availability) for a full breakdown of which sensors appear for which devices.

## Regular Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| AC Input Power | Current AC input power | W |
| AC Output Frequency | Current AC output frequency | Hz |
| AC Output Voltage (Bus) | AC output voltage on the internal bus | V |
| AC Output Voltage (Outlet) | AC output voltage at the outlet terminals | V |
| Battery Connected | Whether an external battery pack is connected | Yes/No |
| Battery Status | Idle, Charging, Discharging, or Fault | text |
| Battery Temperature | Battery temperature | C |
| DC Input Power | Current DC/car input power | W |
| Error Code | Reported device error code | integer |
| Last Updated | Timestamp of last successful data refresh | ISO 8601 |
| Last Offline | When the Jackery cloud last saw the device disconnect | ISO 8601 |
| Last Online | When the Jackery cloud last saw the device connect | ISO 8601 |
| Output Power | Current power output | W |
| Parallel Connection | None / Charge / Discharge | text |
| Remaining Battery | Current battery level | % |
| Remaining Output Time | Estimated remaining runtime | hours |
| Solar Panel Input Power | Current solar panel input power | W |
| Solar Type | None / High Voltage / Low Voltage / High and Low Voltage | text |
| Time to Full | Estimated time to full charge | hours |
| Total Input Power | Current total power input | W |
| UTC Offset | Timezone offset stored on the device (diagnostic, always available). Created when the device reports it | hours |

**Note on Battery Status:** When a portable is connected to and managed by the Smart Transfer Switch, its Battery Status sensor reports Idle even while actively charging. The authoritative charging status in that configuration is the Transfer Switch's AC1 Battery Status or AC2 Battery Status sensor. See [Portable Devices](Portable-Devices#transfer-switch-connection).

**Note on solar and Battery Status:** AC1/AC2 Battery Status (and the portable's own Parallel Connection) only reflect grid-facing charge/discharge through the Transfer Switch. Neither accounts for a connected device's own solar input - confirmed by testing, status still reports "Discharging" even when solar input exceeds the house load. See AC1/AC2 Solar Input Power below for the actual solar contribution.

## Transfer Switch Sensors

These sensors are only created for the Smart Transfer Switch.

### Status and Diagnostics

| Sensor | Description | Unit |
|--------|-------------|------|
| AC1 Error Code | OK or error code (F1-FF) | text |
| AC1 Temperature Alarm | OK / High Temperature / Low Temperature | text |
| AC2 Error Code | OK or error code (F1-FF) | text |
| AC2 Temperature Alarm | OK / High Temperature / Low Temperature | text |
| Active Plan | Currently executing scheduled plan | text |
| Mains Power Fault | OK / Not Connected / Abnormality | text |
| Module Overload | OK / Mains Power Overload / Energy Storage Overload | text |
| Power System State | Power supplied by Grid or Station | text |
| Scheduled Plans | Number of active scheduled plans | integer |

### AC1 Battery Slot

| Sensor | Description | Unit |
|--------|-------------|------|
| AC1 Battery Level | Battery level of device connected to AC1 | % |
| AC1 Battery Packs | Number of add-on battery packs on AC1 | integer |
| AC1 Battery Status | Battery state of device on AC1 | text |
| AC1 Connected | Whether a battery device is connected to AC1 | Yes/No |
| AC1 Input Power | Input power to AC1 | W |
| AC1 Output Power | Output power from AC1 | W |
| AC1 Pack N Battery | Battery level of add-on pack N on AC1 (up to 5) | % |
| AC1 Remaining Time | Estimated remaining runtime for AC1 | hours |
| AC1 Solar Input Power | Solar input power reported by the device connected to AC1 (borrowed from that device's own sensor) | W |
| AC1 Time to Full | Estimated time to full charge for AC1 | hours |

### AC2 Battery Slot

| Sensor | Description | Unit |
|--------|-------------|------|
| AC2 Battery Level | Battery level of device connected to AC2 | % |
| AC2 Battery Packs | Number of add-on battery packs on AC2 | integer |
| AC2 Battery Status | Battery state of device on AC2 | text |
| AC2 Connected | Whether a battery device is connected to AC2 | Yes/No |
| AC2 Input Power | Input power to AC2 | W |
| AC2 Output Power | Output power from AC2 | W |
| AC2 Pack N Battery | Battery level of add-on pack N on AC2 (up to 5) | % |
| AC2 Remaining Time | Estimated remaining runtime for AC2 | hours |
| AC2 Time to Full | Estimated time to full charge for AC2 | hours |

Per-pack sensors include the pack serial number as a state attribute. Individual pack sensors only appear when the pack is physically connected. Add-on packs can take 24 hours or more to populate after being plugged in. Re-adding the base device to the app triggers add-on packs being added immediately to the app/integration.

### Circuits

| Sensor | Description | Unit |
|--------|-------------|------|
| Circuit {name} Power | Per-circuit power consumption | W |

Circuit names are decoded from the device. Unnamed circuits fall back to their index number. Split-phase pairs (240V circuits) are automatically combined into a single entity whose power value is the sum of both legs.

See [Transfer Switch](Transfer-Switch) for more detail on circuit behavior.

## Binary Sensors

| Sensor | Description |
|--------|-------------|
| Cloud Connection | Whether the Jackery cloud reports the device as connected (all devices) |
| AC1 Communication Fault | AC1 communication fault (Transfer Switch) |
| AC2 Communication Fault | AC2 communication fault (Transfer Switch) |
| AC Output | AC output active |
| AC Pass-through | AC power is being passed through |
| Cover Open | Cover open fault (Transfer Switch) |
| DC Car Output | DC car port active |
| DC Output | Combined DC output active |
| Emergency Stop | Emergency stop fault (Transfer Switch) |
| Outlets Active | Any device outlet is active |
| Power Alarm | Device power or protection alarm |
| RTC Fault | Real-time clock fault (Transfer Switch) |
| Temperature Alarm | Device temperature alarm |
| Temperature Fault | NTC temperature fault (Transfer Switch) |
| Temperature Protection | Device temperature protection active |
| Transfer Switch Connected | Device is connected to a Smart Transfer Switch |
| UPS Mode | UPS mode active (Transfer Switch) |
| USB Output | USB output active |

**Note:** Some Jackery models report DC output as a single combined `odc` property; others use separate `odcu` (USB) and `odcc` (car) properties. The combined DC Output entity is hidden when the device reports individual DC properties.
