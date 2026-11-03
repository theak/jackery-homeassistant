# Device Properties Reference

This page documents the raw property keys used by the Jackery protocol, what they mean, and whether the integration maps them to Home Assistant entities.

## Protocol Overview

Device data arrives through two channels:

- **HTTP polling** - The integration periodically fetches a property snapshot from the Jackery API. This covers most sensor values.
- **MQTT** - A persistent connection receives real-time property updates pushed by the device. Some data (circuits, plans) is only available via MQTT queries.

Commands (writing values) are sent via MQTT. It seems more stable to use the persistent connection that is already broadcasting data.

---

## Transfer Switch Properties

Properties marked **MQTT only** are not included in the HTTP snapshot and require an explicit MQTT query.

| Property | Type | Description | Protocol | Integration Entity |
|----------|------|-------------|----------|--------------------|
| `ac1` | object | Battery Slot 1 (see sub-object below) | HTTP | AC1 sensors |
| `ac2` | object | Battery Slot 2 (see sub-object below) | HTTP | AC2 sensors |
| `autoDt` | int | Auto mode backup reserve (%) | HTTP | Auto Mode Backup Reserve number |
| `cds` | list | Charge/discharge plan list | HTTP | Plan switches |
| `cdsDt` | int | Scheduled mode backup reserve (%) | HTTP | Scheduled Mode Backup Reserve number |
| `cep` | object | Currently executing plan | HTTP | Active Plan sensor |
| `cir` | list | Circuit list (see sub-object below) | MQTT only | Circuit sensors/switches |
| `de` | int | Battery discharge today (Wh cumulative) | HTTP | Battery Discharge energy sensor |
| `ddt` | int | Default/current backup reserve (%) | HTTP | Backup Reserve number |
| `dg` | int | Grid consumption today (Wh cumulative) | HTTP | Grid Consumption energy sensor |
| `dh` | int | House consumption today (Wh cumulative) | HTTP | House Consumption energy sensor |
| `ds` | int | Solar generation today (Wh cumulative) | HTTP | Solar Generation energy sensor |
| `dt` | int | Legacy backup reserve (%) | HTTP | Not mapped** |
| `en` | int | Working mode (0=Auto, 1=Scheduled, 2=Self) | HTTP | Working Mode select |
| `fz` | object | Fault zone (see sub-object below) | HTTP | Fault sensors |
| `ip` | int | Input power (W) | HTTP | Total Input Power sensor |
| `op` | int | Output power (W) | HTTP | Output Power sensor |
| `ot` | int | Remaining output time | HTTP | Remaining Output Time sensor |
| `pss` | int | Power system state (0=Grid, 1=Station) | HTTP | Power System State sensor + Grid/Station switch |
| `rb` | int | Remaining battery (%) | HTTP | Remaining Battery sensor |
| `rc` | int | Rapid/force charging (0=off, 1=on) | HTTP | Force Charge switch |
| `selfDt` | int | Self Consumption mode backup reserve (%) | HTTP | Self Consumption Mode Backup Reserve number |
| `storm` | list | Weather/storm events | MQTT only | Not mapped (location-based alert system, complex) |
| `ups` | int | UPS mode (0=off, 1=on) | HTTP | UPS Mode switch + binary sensor |
| `wps` | int | WiFi Protected Setup (0=off, 1=on) | HTTP | WiFi Protected Setup switch |

### AC Slot Sub-Object (ac1 / ac2)

| Field | Type | Description | Integration Entity |
|-------|------|-------------|-------------------|
| `acpsp` | int | Solar panel power (/10 = W) | Borrowed from connected device by serial match - see AC1/AC2 Solar Input Power sensor |
| `bi` | int | Battery connected (0=no, 1=yes) | AC1/AC2 Connected sensor |
| `bp` | list | Add-on battery packs (see BatteryPack below) | AC1/AC2 Battery Packs count + per-pack sensors |
| `bs` | int | Battery status (0=Idle, 1=Charging, 2=Discharging, 3=Fault) | AC1/AC2 Battery Status sensor |
| `ip` | int | Input power (W) | AC1/AC2 Input Power sensor |
| `it` | int | Time to full | AC1/AC2 Time to Full sensor |
| `mc` | int | Model code | Not mapped |
| `op` | int | Output power (W) | AC1/AC2 Output Power sensor |
| `ot` | int | Remaining output time | AC1/AC2 Remaining Time sensor |
| `rb` | int | Remaining battery (%) | AC1/AC2 Battery Level sensor |
| `sn` | str | Serial number | Not mapped (device attribute) |
| `ss` | int | Solar status (0=none, 1=high V, 2=low V, 3=both) | AC1/AC2 Solar Type sensor |
| `trb` | int | Total battery % across station + all packs combined | AC1/AC2 Total Battery sensor |

### Add-on Battery Pack Sub-Object (bp items in ac1/ac2)

| Field | Type | Description | Integration Entity |
|-------|------|-------------|-------------------|
| `rb` | int | Pack remaining battery (%) | AC1/AC2 Pack N Battery sensor |
| `sn` | str | Pack serial number | State attribute on pack sensor |

### Fault Zone Sub-Object (fz)

| Field | Type | Description | Integration Entity |
|-------|------|-------------|-------------------|
| `bs1` | int | AC1 communication fault | AC1 Communication Fault binary sensor |
| `bs2` | int | AC2 communication fault | AC2 Communication Fault binary sensor |
| `ec1` | int | AC1 error code (0=OK, non-zero=F1-FF) | AC1 Error Code sensor |
| `ec2` | int | AC2 error code (0=OK, non-zero=F1-FF) | AC2 Error Code sensor |
| `es` | int | Emergency stop | Emergency Stop binary sensor |
| `gs` | int | Mains power fault (0=OK, 1=not connected, 2=abnormal) | Mains Power Fault sensor |
| `loc` | str | Line overload | Not mapped |
| `moc` | int | Module overload (0=OK, 1=mains overload, 2=storage overload) | Module Overload sensor |
| `ntc` | int | NTC temperature fault | Temperature Fault binary sensor |
| `ol` | int | Cover open fault | Cover Open binary sensor |
| `rtc` | int | RTC fault | RTC Fault binary sensor |
| `ta1` | int | AC1 temperature alarm (0=OK, 1=high, 2=low) | AC1 Temperature Alarm sensor |
| `ta2` | int | AC2 temperature alarm (0=OK, 1=high, 2=low) | AC2 Temperature Alarm sensor |

### Circuit Sub-Object (cir items)

| Field | Type | Description |
|-------|------|-------------|
| `idx` | int | Circuit index (0-11) |
| `nm` | str | Circuit name (base64-encoded) |
| `pc` | int | Power consumption (W) |
| `pr` | int | Priority |
| `sph` | int | Split-phase partner index (-1 = not paired) |
| `sph_pc` | int | Split-phase partner power consumption |
| `sw` | int | Switch state (0=off, 1=on) |

### WiFi Network Diagnostics

| Field | Type | Description | Integration Entity |
|-------|------|-------------|-------------------|
| `wsig` | int | WiFi signal strength (RSSI) in dBm | WiFi Signal Strength sensor |
| `wname` | str | WiFi network SSID | WiFi Network Name sensor |
| `wip` | str | WiFi IP address assigned to Transfer Switch | WiFi IP Address sensor |
| `mac` | str | MAC address of Transfer Switch WiFi interface | MAC Address sensor |

---

## Portable Station Properties

| Property | Type | Description | Protocol | Integration Entity |
|----------|------|-------------|----------|--------------------|
| `accd` | int | AC output countdown remaining (seconds) | HTTP | AC Output Countdown sensor |
| `acdt` | int | AC delay timer config | HTTP | Not mapped (range/write semantics unresolved) |
| `acip` | int | AC input power (W) | HTTP | AC Input Power sensor |
| `acmode` | int | AC output mode (0=normal, 1=timer) | HTTP | AC Output Mode sensor |
| `acohz` | int | AC output frequency (Hz) | HTTP | AC Output Frequency sensor |
| `acov` | int | AC output voltage bus (/10 = V) | HTTP | AC Output Voltage (Bus) sensor |
| `acov1` | int | AC outlet voltage (/10 = V) | HTTP | AC Output Voltage (Outlet) sensor |
| `acps` | int | AC power status | HTTP | AC Power Status sensor |
| `acpss` | int | AC pass-through status (0=inactive) | HTTP | AC Pass-through binary sensor |
| `acpsp` | int | Solar panel power (/10 = W) | HTTP | Solar Panel Input Power sensor |
| `ast` | int | Auto shutdown timer (minutes) | HTTP | Auto Shutdown number |
| `bc` | int | Battery cutoff (%) | HTTP | Battery Cutoff sensor |
| `box` | int | Connected to Transfer Switch (0/1) | HTTP | Transfer Switch Connected binary sensor |
| `bpc` | int | Undetermined battery-pack-related value | HTTP | Not mapped (meaning/range unresolved) |
| `bs` | int | Battery status (0=Idle, 1=Charging, 2=Discharging, 3=Fault) | HTTP | Battery Status sensor |
| `bt` | int | Battery temperature (/10 = C) | HTTP | Battery Temperature sensor |
| `cip` | int | DC/solar input power (W) | HTTP | DC Input Power sensor |
| `cl` | int | Charge limit (%) | HTTP | Charge Limit sensor |
| `cop` | int | Car (12V) output power (W) | HTTP | Car (12V) Output Power sensor |
| `cs` | int | Charge speed | HTTP | Charge Speed select |
| `dhg_recall` | int | Restore previous output state after startup (0=off, 1=on) | HTTP | Discharge Memory switch |
| `dl` | int | Discharge limit (%) | HTTP | Discharge Limit sensor |
| `dt` | int | Portable backup reserve (%) | HTTP | Portable Backup Reserve sensor |
| `ec` | int | Error code | HTTP | Error Code sensor |
| `en` | int | Working mode (reported when box=1) | HTTP | Not mapped |
| `iac` | int | Input AC connected status | HTTP | AC Input Connected binary sensor |
| `iacPw` | int | Portable AC input power variant (W) | HTTP | AC Input Power (Portable) sensor |
| `idc` | int | Input DC connected status | HTTP | DC Input Connected binary sensor |
| `ip` | int | Total input power (W) | HTTP | Total Input Power sensor |
| `ipalPw` | int | Input from the parallel port (W) | HTTP | Parallel Input Power sensor |
| `it` | int | Time to full (/10 = hours) | HTTP | Time to Full sensor |
| `lm` | int | Light mode (0=off, 1=low, 2=high, 3=sos) | HTTP | Light Mode select |
| `lps` | int | Battery protection (0=full, 1=eco) | HTTP | Battery Protection select |
| `oac` | int | AC output active (0/1) | HTTP | AC Output binary sensor + switch |
| `oac2` | int | Second AC output | HTTP | Second AC Outlet binary sensor |
| `oacPw` | int | AC output power per-port (W) | HTTP | AC Output Power sensor |
| `oact` | int | AC output countdown (seconds) | HTTP | AC Output Countdown sensor |
| `odc` | int | DC output (0/1) | HTTP | DC Output binary sensor + switch |
| `odcc` | int | DC car output (0/1) | HTTP | DC Car Output binary sensor + switch |
| `odcct` | int | DC car countdown (seconds) | HTTP | DC Car Output Countdown sensor |
| `odcPrio` | int | DC output priority (0/1) | HTTP | DC Output Priority switch |
| `odcPrioSoc` | int | DC priority SOC threshold (%) | HTTP | DC Priority SOC Threshold sensor |
| `odct` | int | DC output countdown (seconds) | HTTP | DC Output Countdown sensor |
| `odcu` | int | USB output (0/1) | HTTP | USB Output binary sensor + switch |
| `odcut` | int | USB countdown (seconds) | HTTP | USB Output Countdown sensor |
| `op` | int | Output power (W) | HTTP | Output Power sensor |
| `opalPw` | int | Output to the parallel port (W) | HTTP | Parallel Output Power sensor |
| `ot` | int | Remaining output time (/10 = hours) | HTTP | Remaining Output Time sensor |
| `outPrio` | int | AC output priority (0/1) | HTTP | AC Output Priority switch |
| `pal` | int | Power alarm (0/1) | HTTP | Power Alarm binary sensor |
| `pc` | int | Parallel connection (0=none, 1=charge, 2=discharge) | HTTP | Parallel Connection sensor |
| `pm` | int | Energy saving mode | HTTP | Energy Saving number |
| `pmb` | int | Outlets active (0/1) | HTTP | Outlets Active binary sensor |
| `pss` | int | Power system state | HTTP | Not mapped (TS-side sensor) |
| `rb` | int | Remaining battery (%) | HTTP | Remaining Battery sensor |
| `sfc` | int | Super fast charge (0/1) | HTTP | Super Fast Charge switch |
| `sltb` | int | Screen timeout | HTTP | Screen Timeout number |
| `ss` | int | Solar status (0=normal, 1=high V, 2=low V, 3=both) | HTTP | Solar Type sensor |
| `ta` | int | Temperature alarm (0/1) | HTTP | Temperature Alarm binary sensor |
| `tmt` | int | Auto shutdown timer value | HTTP | Not mapped (use `ast`) |
| `tp` | int | Temperature protection (0/1) | HTTP | Temperature Protection binary sensor |
| `tt` | int | Temperature threshold (when box=1) | HTTP | Temperature Threshold sensor |
| `ups` | int | UPS mode (0/1) | HTTP | UPS Mode binary sensor + switch |
| `usba1` | int | USB-A port 1 power (W) | HTTP | USB-A Port 1 Power sensor |
| `usba2` | int | USB-A port 2 power (W) | HTTP | USB-A Port 2 Power sensor |
| `usba3` | int | USB-A port 3 power (W) | HTTP | USB-A Port 3 Power sensor |
| `usbc1` | int | USB-C port 1 power (W) | HTTP | USB-C Port 1 Power sensor |
| `usbc2` | int | USB-C port 2 power (W) | HTTP | USB-C Port 2 Power sensor |
| `usbc3` | int | USB-C port 3 power (W) | HTTP | USB-C Port 3 Power sensor |
| `wss` | int | WiFi signal status | HTTP | WiFi Signal Status sensor |

---

## Notes

- The `bs` (Battery Status) property on a portable reports `0` (Idle) when the device is connected to and managed by a Transfer Switch. Use the Transfer Switch's `ac1.bs` / `ac2.bs` instead. See [Portable Devices](Portable-Devices#transfer-switch-connection).
- The Transfer Switch's `ac1`/`ac2` object does not report `acpsp`. The integration creates AC1/AC2 Solar Input Power by matching `ac1.sn`/`ac2.sn` against the account's other devices and reading that device's `acpsp`.
- `ac1.bs`/`ac2.bs` and the portable's own `pc` (Parallel Connection) only reflect grid-facing charge/discharge through the Transfer Switch's AC port - confirmed by testing, they still report "Discharging" even when a connected device's solar input exceeds the house load. Neither is a true net (grid + solar) charge indicator.
- Some portable properties (`en`, `dt`, `dl`, `cl`) only appear or become meaningful when `box=1` (connected to a Transfer Switch).
- The `sltb` property is the read key for screen timeout; the write command uses a different key (`slt`).
