# Device Availability

The integration creates entities dynamically based on what properties the Jackery API reports for each device. Not all entities appear for all devices.

## General Rules

- Entities are created only when the device reports the underlying property key.
- No entities are created for properties the API does not return for a given device.
- DC output behavior differs by model: see [DC Output Variants](#dc-output-variants) below.

## Transfer Switch-Only Entities

The following entities are only created for the Smart Transfer Switch:

**Sensors:**
- Scheduled Plans, Active Plan
- Mains Power Fault, AC1/AC2 Error Codes, AC1/AC2 Temperature Alarms, Module Overload
- AC1/AC2 battery slot sensors (Battery Level, Output/Input Power, Remaining Time, Time to Full, Battery Status, Connected, Battery Packs, per-pack Battery Level)
- Per-circuit power sensors

**Binary Sensors:**
- Emergency Stop, AC1/AC2 Communication Fault, Cover Open, Temperature Fault, RTC Fault

**Switches:**
- Grid / Station, Force Charge, UPS Mode
- Per-circuit switches
- Per-plan toggle switches

**Selects:**
- Working Mode

**Numbers:**
- Backup Reserve

## Portable Device-Only Entities

The following entities are only created for portable power stations:

**Switches:**
- Charging Plan

**Text:**
- Charging Plan Time

**Selects:**
- Charging Plan Repeat

`Charging Plan` appears when the device reports DP 107. `Charging Plan Time` and `Charging Plan Repeat` appear when the device reports DP 108. These entities become unavailable if the DP 108 payload is missing or malformed.

Individual portable **Charging Plan** entities are not available for devices currently connected to a Smart Transfer Switch.

## Fault Diagnostic Entities

Fault entities (both multi-state sensors and binary sensors) are created when the device reports an `fz` sub-object in its property data. All fault entities use the diagnostic entity category.

## AC1/AC2 Battery Slot Sensors

AC1 and AC2 slot sensors appear when the Transfer Switch reports `ac1` or `ac2` sub-objects respectively.

Per-pack battery level sensors (`AC1 Pack N Battery`) appear only when a pack is physically connected. After a pack is first plugged in, it can take 24 hours or more before the sensor is created, as the device registers the pack over time.

## Circuit Entities

Circuit power sensors and on/off switches appear for Transfer Switch devices. Split-phase pairs are automatically detected and combined into single entities.

## Cloud Connection and Offline Devices

Every device gets a **Cloud Connection** binary sensor, plus **Last Online** and **Last Offline** timestamp sensors, from the `onlineStatus`, `onlineTime` and `offlineTime` fields the Jackery cloud returns with each device.

When the cloud reports a device offline, all of that device's other entities become unavailable rather than showing the last values received. Cloud Connection, Last Online, Last Offline and Last Updated stay available. After the device has been offline for 10 minutes, a Repair issue is raised; it clears automatically when the device reconnects. See [Troubleshooting](Troubleshooting#device-offline-from-the-jackery-cloud).

## DC Output Variants

Some Jackery models report DC output as a single combined `odc` property. Others report separate USB (`odcu`) and DC car (`odcc`) properties. When a device reports the separate properties, the combined DC Output entities (sensor and switch) are hidden and only the individual USB and car entities appear.

## UPS Mode

The UPS Mode switch and UPS Mode binary sensor are created for the Transfer Switch. UPS Mode is not available on standalone portable devices.

## Transfer Switch Connected

The Transfer Switch Connected binary sensor appears on portable devices when the `box` property is reported by the API.
