# Charging Plans

Scheduled charge/discharge plans allow the Smart Transfer Switch to automatically charge or discharge the connected batteries during specific time windows. Plans are used by the **Scheduled Tasks** working mode.

See [Transfer Switch - Working Modes](Transfer-Switch#working-modes) for how plans relate to the other operating modes.

## Overview

Each plan defines:

- Whether it is a charge or discharge event
- A start and end time
- Which days of the week it is active
- Whether it is currently enabled

Plans are managed through the `jackery.create_plan`, `jackery.update_plan`, and `jackery.delete_plan` Home Assistant services, or through the [Plan Management Lovelace card](Lovelace-Cards#transfer-switch-plan-management-card).

See [Services](Services) for full field documentation and examples.

## Plan Data Structure

Each plan has the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `et` | string | End time in `HH:MM` format |
| `lps` | string | 7-character day mask, Monday through Sunday (`"1111100"` = weekdays) |
| `pid` | string | Plan ID, used to reference the plan in update and delete operations |
| `st` | string | Start time in `HH:MM` format |
| `sw` | integer | Enabled: `1` = on, `0` = off |
| `tt` | integer | Type: `1` = Charge, `2` = Discharge |

Plan IDs are timestamp-based strings assigned by the device when a plan is created.

## Integration Entities

For each plan, the integration creates:

- A **Plan toggle switch** to enable or disable the plan without deleting it.

In addition, the integration provides:

- A **Scheduled Plans** sensor showing how many plans exist.
- An **Active Plan** sensor showing which plan is currently executing (or `none` when no plan is running).

Plan entities are only created for the Smart Transfer Switch.

## Plan Caching

Plans are not included in the HTTP property snapshot. They are queried via the persistent MQTT connection. The integration:

- Pre-seeds plan entities before the first coordinator refresh so they are available immediately after setup.
- Queries for plan updates periodically via MQTT.
- Does not overwrite the cached plan data if a query returns an empty result, to prevent transient failures from clearing the display.

Plan switch names are set at startup from the initial plan data. If plan data is temporarily unavailable, the switch falls back to the last known name from the cache.

## MQTT Protocol Notes

Plans use special MQTT message types rather than the standard `DevicePropertyChange` type used for most property changes.

| Action | messageType | actionId | Body |
|--------|-------------|----------|------|
| Create plan | `InsertElectricityStrategy` | 13 | `{"cmd": 16, ...plan fields}` |
| Delete plan | `DeleteElectricityStrategy` | 15 | `{"cmd": 18, "pid": "<id>"}` |
| Get active plan | `QueryCurrentElectricityStrategy` | 18 | `{"cmd": 21}` |
| List all plans | `QueryElectricityStrategy` | 12 | `{"cmd": 15}` |
| Update plan | `UpdateElectricityStrategy` | 14 | `{"cmd": 17, ...plan fields}` |

### Sample Query Response

```json
{
  "actionId": 12,
  "messageType": "QueryElectricityStrategy",
  "deviceSn": "855125010301866",
  "body": {
    "cmd": 15,
    "cds": [
      {
        "pid": "1757967897",
        "tt": 2,
        "st": "14:00",
        "et": "19:00",
        "sw": 1,
        "lps": "1111100"
      }
    ]
  }
}
```

The Active Plan query returns `"cep": null` in the body when no plan is currently executing.
