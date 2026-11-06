# Transfer Switch

This page covers features specific to the Jackery Smart Transfer Switch (JA-TS02A / model HTO785A).

## Overview

The Smart Transfer Switch bridges the utility grid and connected Jackery battery devices. It can automatically switch between grid and battery power, manage charging schedules, and monitor per-circuit power consumption.

## Working Modes

The Transfer Switch operates in one of three working modes, controlled by the **Working Mode** select entity.

| Mode | `en` Value | Description |
|------|-----------|-------------|
| Automatic Charging | `0` | Automatically manages charging from the grid based on backup reserve |
| Scheduled Tasks | `1` | Uses configured charge/discharge plans to control when to charge or discharge |
| Self Consumption | `2` | Prioritizes battery and solar output; charges from the grid only when needed |

Each mode has its own backup reserve percentage (the minimum battery level held in reserve for outages). The backup reserve for the currently active mode is shown in the **Backup Reserve** number entity and can be adjusted there directly.

The integration also exposes **Auto Mode Backup Reserve**, **Scheduled Mode Backup Reserve**, and **Self Consumption Mode Backup Reserve** number entities. The Jackery app doesn't provide controls for these, they're either ignored or used to set the global **Backup Reserve** value. Probably.

See [Charging Plans](Charging-Plans) for details on setting up scheduled charge/discharge plans used by Scheduled Tasks mode.

## Grid / Station Toggle

The **Grid / Station** switch selects whether the home loads are powered by the utility grid or by the connected battery devices. Toggling this switch does not change the working mode.

## UPS Mode

The **UPS Mode** switch enables approximately 20ms grid-to-battery switchover on a power interruption. When UPS Mode is enabled, the **UPS Mode** binary sensor also reflects the active state.

## Force Charge

The **Force Charge** switch forces the battery to charge from the grid regardless of the current working mode or scheduled plans. Useful for quickly topping up before an expected outage.

## Timezone and Schedules

The Transfer Switch runs its scheduled plans on its own clock, set from a UTC offset stored on the device. The **UTC Offset** number shows and changes that offset in hours. The Jackery app only updates it when you open the app, so after a daylight saving change the switch can keep running plans an hour early or late.

Turn on **Follow Home Assistant Timezone** to have the integration compare the device's offset with Home Assistant's and correct it when they differ. It also reacts when you change the timezone in Home Assistant's settings. The switch is off by default and keeps its state across restarts. While it is on, the UTC Offset number still shows the offset but rejects changes. The UTC Offset diagnostic sensor always shows the device's current offset.

The Explorer 5000 Plus also has these two entities. It only accepts the offset and it has no effect while it is connected to the Transfer Switch.

## Energy Counters

The Transfer Switch reports cumulative energy totals in watt-hours:

| Sensor | Property | Description |
|--------|----------|-------------|
| Solar Generation | `ds` | Total solar energy generated |
| House Consumption | `dh` | Total household energy consumed |
| Battery Discharge | `de` | Total battery energy discharged |
| Grid Consumption | `dg` | Total grid energy consumed |

## WiFi Controls and Diagnostics

The **WiFi Protected Setup** switch controls the Transfer Switch's WPS quick-connect function.

The following diagnostic sensors expose the network information reported by the device:

| Sensor | Property |
|--------|----------|
| WiFi Signal Strength | `wsig` |
| WiFi Network Name | `wname` |
| WiFi IP Address | `wip` |
| MAC Address | `mac` |

The protocol also contains `wpc` and `storm` fields, but their behavior is undocumented and not found in the app. The `fz.loc` line-overload field is also unknown.

## Circuits

The Transfer Switch monitors and controls individual circuits in the connected electrical panel.

### Circuit Entities

For each logical circuit, the integration creates:

- A **power sensor** showing current power consumption in watts.
- An **on/off switch** to toggle the circuit breaker.

Circuit names are decoded from the device configuration. Circuits without a configured name fall back to their index number.

### Split-Phase Pairs

240V circuits use two legs (split-phase). The integration automatically detects paired legs using the `sph` cross-reference index and combines them into a single entity. The combined power sensor reports the sum of both legs. Toggling the combined switch toggles both legs together.

### Circuit Data Availability

Circuit data is not included in the HTTP property snapshot. It is queried on startup via the persistent MQTT connection. Entities are pre-seeded from that initial query so they are available immediately after setup. Updates are received from the device via the same persistent MQTT connection as circuit states change.

### Circuit Physical Status

The Jackery Transfer Switch does *NOT* monitor or show the physical status of the circuit breakers. If the breaker physically trips the Transfer Switch will happily show the circuit as active, because in the software it technically is. For important loads like refrigerators it is probably still prudent to have a power monitoring plug of some kind for redundancy.

## AC1 and AC2 Battery Slots

The Transfer Switch has two AC output ports (AC1 and AC2) that can each connect to a Jackery portable power station. The integration creates a set of diagnostic sensors for each connected device.

Each slot includes a **Solar Type** sensor that reports None, High Voltage, Low Voltage, or High & Low Voltage. The **Total Battery** sensor reports the combined percentage across the connected station and all of its add-on battery packs.

See [Sensors - AC1 and AC2 Battery Slots](Sensors#ac1-battery-slot) for the full sensor list.

### Battery Pack Add-ons

Each connected portable can have up to five add-on battery packs. The integration creates individual battery level sensors for each detected pack (`AC1 Pack 1 Battery` through `AC1 Pack 5 Battery`). Each sensor includes the pack serial number as a state attribute.

Pack sensors only appear when the pack is physically connected. After a pack is first plugged in it can take 24 hours or more before the sensor appears. Re-adding the base device to the app triggers add-on packs being added immediately to the app/integration.

### Charging Status When Connected

When a portable is connected to the Transfer Switch, the portable's own Battery Status sensor reports Idle even when it is actively charging. The authoritative charging status is the **AC1 Battery Status** or **AC2 Battery Status** sensor on the Transfer Switch device.

**AC1/AC2 Battery Status only reflects the AC1/AC2 port's grid-facing flow** (charging from grid vs. discharging to the house through the Transfer Switch), not a true net reading. Confirmed by testing: when solar input exceeds the house load, the status still reports "Discharging" - it does not account for a connected device's own solar input. Use the **AC1/AC2 Solar Input Power** sensor alongside Battery Status to see the full picture; there is no single field that reports true net (grid + solar) charge direction.

### Solar Input Per Slot

The Transfer Switch's `ac1`/`ac2` property object does not itself report solar input. The integration instead matches the slot's connected device serial number (`ac1.sn`) against the account's other devices and borrows that device's own **Solar Panel Input Power** reading, exposed as **AC1 Solar Input Power** / **AC2 Solar Input Power**. This only appears when the connected device actually reports solar input.

## Fault Diagnostics

The Transfer Switch reports fault conditions through the `fz` property object. The integration flattens these into individual entities.

### Multi-State Fault Sensors

| Sensor | States |
|--------|--------|
| AC1 Error Code | OK or error code F1-FF |
| AC1 Temperature Alarm | OK / High Temperature / Low Temperature |
| AC2 Error Code | OK or error code F1-FF |
| AC2 Temperature Alarm | OK / High Temperature / Low Temperature |
| Mains Power Fault | OK / Not Connected / Abnormality |
| Module Overload | OK / Mains Power Overload / Energy Storage Overload |

### Binary Fault Sensors

| Sensor | Description |
|--------|-------------|
| AC1 Communication Fault | AC1 communication fault |
| AC2 Communication Fault | AC2 communication fault |
| Cover Open | Cover open fault |
| Emergency Stop | Emergency stop fault |
| RTC Fault | Real-time clock fault |
| Temperature Fault | NTC temperature fault |

Fault entities are created when the device reports the `fz` sub-object. All fault entities are in the diagnostic entity category.
