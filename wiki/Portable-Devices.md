# Portable Devices

This page covers features and behavior specific to Jackery portable power stations (Explorer series and similar).

## Supported Models

The integration supports any Jackery device that reports data through the Jackery cloud API. Verified tested models include:

- Explorer 5000 Plus (model HTE1195000A)
- Explorer 300 Plus (model HTE095300A)

Other Plus series models that use the same protocol should work but may report a different subset of properties.

## Sensors and Controls

Portable devices expose the standard sensor and control set. See [Sensors](Sensors) and [Controls](Controls) for the full tables. The properties available for a given device depend on what the Jackery API reports for that model.

### DC Output Variants

Some models expose DC output as a single combined `odc` switch. Others expose separate USB (`odcu`) and DC car (`odcc`) switches. When a device reports separate properties, the combined DC Output entity is hidden and only the individual entities appear.

### Parallel Connection

The `pc` property reports whether the device is connected to another unit for parallel charging or discharging: None, Charge, or Discharge.

### Solar Input

Solar panel input power is reported via the `cip` property. Not all models include solar ports.

### Deferred Controls

Some reported settings remain read-only because their behavior can't be verified without testing:

- `acdt` is a writable AC delay timer, but its supported range and app behavior need hardware verification.
- `bpc` is battery-pack-related, but its exact meaning and range remain unresolved.
- `dl`, `cl`, and `bc` are battery boundary values that the app writes together. The app derives `bc` from `cl`, so independent number controls could produce invalid combinations.
- `odcPrioSoc` has a write command, but its supported range and interaction with output-priority settings need hardware verification.

## Charging Plans (DP 107/108)

Portable Plus models support a simple charging plan for controlling when the device charges. This is separate from the Transfer Switch scheduled plan system.

- The **Charging Plan** switch (DP 107) enables or disables the plan.
- The **Charging Plan Time** text entity (DP 108) sets the active time window in `HH:mm-HH:mm` format.
- The **Charging Plan Repeat** select entity sets the repeat schedule: Everyday, Weekdays, Weekends, or Once.

These entities become unavailable if the DP 108 payload is missing or malformed.

Portable charging plans are not managed through the `jackery.create_plan` / `jackery.update_plan` / `jackery.delete_plan` services. Those services are for Transfer Switch scheduled plans only.

## Transfer Switch Connection

When a portable is connected to the Smart Transfer Switch:

- The `box` property indicates the connection (`1` = connected).
- The **Transfer Switch Connected** binary sensor reflects this state.
- The portable's own **Battery Status** (`bs`) reports Idle (`0`) while the Transfer Switch is managing charging, even when the battery is actively being charged. The authoritative charging status in this configuration is the Transfer Switch's **AC1 Battery Status** or **AC2 Battery Status** sensor.
- The portable **Charging Plan** switch, **Charging Plan Time**, and **Charging Plan Repeat** entities become unavailable. Charging is managed by the Transfer Switch instead. Use the Transfer Switch's [Charging Plans](Charging-Plans) and Working Mode controls.

## Battery Pack Add-ons

Devices that support add-on battery packs report them via the `ac1` or `ac2` sub-objects when connected to a Transfer Switch. See [Transfer Switch - AC1 and AC2 Battery Slots](Transfer-Switch#ac1-and-ac2-battery-slots) for details on those sensors.
