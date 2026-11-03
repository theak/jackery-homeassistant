# Example Automations

Replace entity IDs in these examples with the actual entity IDs from your Home Assistant instance.

---

## Portable Device Automations

### Low Battery Alert

Sends a notification when the battery drops below 20%.

```yaml
automation:
  alias: "Jackery Low Battery Alert"
  trigger:
    platform: numeric_state
    entity_id: sensor.jackery_explorer_5000_remaining_battery
    below: 20
  action:
    service: notify.mobile_app
    data:
      message: >
        Jackery battery low: {{ states('sensor.jackery_explorer_5000_remaining_battery') }}%
```

### AC Output On Notification

Sends a notification when the AC output activates.

```yaml
automation:
  alias: "Jackery AC Output On"
  trigger:
    platform: state
    entity_id: binary_sensor.jackery_explorer_5000_ac_output
    to: "on"
  action:
    service: notify.mobile_app
    data:
      message: "Jackery AC output has been turned on"
```

---

## Transfer Switch Automations

### Switch to Self Consumption During Peak Hours

Switches the Transfer Switch to Self Consumption mode at the start of peak rate hours, then returns to Automatic Charging afterward. Adjust the times to match your utility rate schedule.

```yaml
automation:
  - alias: "Transfer Switch: Peak Hours Start (Self Consumption)"
    trigger:
      platform: time
      at: "14:00:00"
    action:
      service: select.select_option
      target:
        entity_id: select.jackery_transfer_switch_working_mode
      data:
        option: "Self Consumption"

  - alias: "Transfer Switch: Peak Hours End (Auto Charging)"
    trigger:
      platform: time
      at: "19:00:00"
    action:
      service: select.select_option
      target:
        entity_id: select.jackery_transfer_switch_working_mode
      data:
        option: "Automatic Charging"
```

### Force Charge Before a Storm

Uses a weather trigger (or manual script) to force-charge before a weather event. Replace the trigger with whatever fits your setup.

```yaml
automation:
  alias: "Transfer Switch: Force Charge Before Storm"
  trigger:
    platform: state
    entity_id: weather.home
    to: "lightning-rainy"
  action:
    service: switch.turn_on
    target:
      entity_id: switch.jackery_transfer_switch_force_charge
```

---

## Device Offline Notification

A Repair issue is raised automatically after a device has been offline for 10 minutes. This automation adds a phone notification. Replace the entity IDs and notify service with your own.

```yaml
automation:
  alias: "Jackery Device Offline"
  trigger:
    platform: state
    entity_id:
      - binary_sensor.explorer_5000_cloud_connection
    to: "off"
    for:
      minutes: 10
  action:
    service: notify.mobile_app_your_phone
    data:
      title: "Jackery offline"
      message: >
        {{ trigger.to_state.attributes.friendly_name | replace(" Cloud Connection", "") }}
        lost its cloud connection. Re-enable Wi-Fi on the device and re-add it in the Jackery app.
```
