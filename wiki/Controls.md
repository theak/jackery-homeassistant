# Controls

All writable entities created by the integration. Entities are created only when the Jackery API reports the underlying property for that device. Transfer Switch-only controls are labeled accordingly.

See [Device Availability](Device-Availability) for a full breakdown of which controls appear for which devices.

## Switches

| Entity | Description |
|--------|-------------|
| AC Output | Toggle AC output |
| Charging Plan | Enable or disable charging plans |
| Circuit {name} | Toggle individual circuits on/off (Transfer Switch) |
| DC Car Output | Toggle DC car output |
| DC Output | Toggle combined DC output |
| Follow Home Assistant Timezone | Keep the device's UTC offset in step with Home Assistant, including daylight saving changes. Off by default.
| Force Charge | Force battery to charge from grid regardless of working mode (Transfer Switch) |
| Grid / Station | Toggle between grid power and station power (Transfer Switch) |
| Plan {name} | Toggle individual scheduled plans on/off (Transfer Switch) |
| Super Fast Charge | Toggle super fast charge mode |
| UPS Mode | Toggle UPS mode (Transfer Switch) |
| USB Output | Toggle USB output |

**Note on DC output:** Some models split DC control into separate USB (`odcu`) and car (`odcc`) entities instead of a single combined DC Output switch.

**Note on Transfer Switch connection:** When a portable is connected to the Smart Transfer Switch, the Charging Plan switch and related entities (Charging Plan Time, Charging Plan Repeat) become unavailable. The Transfer Switch takes over charging management. Circuit and Plan switches are described in detail on the [Transfer Switch](Transfer-Switch) and [Charging Plans](Charging-Plans) pages.

## Selects

| Entity | Options |
|--------|---------|
| Battery Protection | `full`, `eco` |
| Charge Speed | `fast`, `mute` |
| Charging Plan Repeat | `Everyday`, `Weekdays`, `Weekends`, `Once` |
| Light Mode | `off`, `low`, `high`, `sos` |
| Working Mode | `Automatic Charging`, `Scheduled Tasks`, `Self Consumption` (Transfer Switch) |

Working Mode controls which of the three Transfer Switch operating modes is active. See [Transfer Switch](Transfer-Switch) for details on each mode.

**Battery Protection:**
- `full` - Uses the full battery capacity (0-100%).
- `eco` - Limits charge to 85% to reduce battery wear.

**Charge Speed:**
- `fast` - Charges at full speed.
- `mute` - Charges slower to lower fan noise.

**Light Mode:** Not all devices support all light modes. The available options depend on the device model. Devices without a built-in LED will not report the `lm` property or have the Light Mode entity.

## Numbers

| Entity | Description | Range | Unit |
|--------|-------------|-------|------|
| Auto Shutdown | Auto shutdown delay | device-dependent | minutes |
| Energy Saving | Energy saving timer | device-dependent | minutes |
| Screen Timeout | Screen timeout delay | device-dependent | minutes |
| Backup Reserve | Minimum battery % reserved for outages (Transfer Switch) | 1-90 | % |
| UTC Offset | Timezone offset the device uses for its clock and schedules | -12 to 14, 0.25 steps | hours |

**UTC Offset:** Changes are sent a few seconds after you stop adjusting the value, so stepping with the arrows sends a single update. The value is unavailable while **Follow Home Assistant Timezone** is on. See [Transfer Switch](Transfer-Switch#timezone-and-schedules).

## Text

| Entity | Description | Format |
|--------|-------------|--------|
| Charging Plan Time | Charging plan time window for supported devices | `HH:mm-HH:mm` |
