# Services

The integration registers Home Assistant services for managing Transfer Switch charge/discharge scheduled plans. These services do not apply to portable device charging plans. They can be called from automations, scripts, or Developer Tools.

| Service | Description |
|---------|-------------|
| `jackery.create_plan` | Create a new Transfer Switch charge or discharge plan |
| `jackery.delete_plan` | Delete a Transfer Switch plan by its ID |
| `jackery.update_plan` | Update an existing Transfer Switch plan |

Plan IDs (`pid`) are visible as state attributes on the individual Plan switch entities and on the Scheduled Plans sensor.

See [Charging Plans](Charging-Plans) for background on how plans work and how they interact with Working Modes.

---

## `jackery.create_plan`

| Field | Required | Type | Description | Example |
|-------|----------|------|-------------|---------|
| `days` | Yes | string | 7-character day mask, Monday through Sunday | `"1111100"` |
| `enabled` | No | boolean | Whether the plan starts enabled (default: `true`) | `true` |
| `end_time` | Yes | string | End time in `HH:MM` format | `"19:00"` |
| `start_time` | Yes | string | Start time in `HH:MM` format | `"14:00"` |
| `type` | Yes | integer | `1` = Charge, `2` = Discharge | `2` |

**Day mask format:** Each character is `1` (enabled) or `0` (disabled) for the corresponding day of the week, starting Monday. For example, `"1111100"` enables the plan on weekdays only and `"0000011"` enables it on weekends only.

### Example

```yaml
service: jackery.create_plan
data:
  type: 2
  start_time: "14:00"
  end_time: "19:00"
  days: "1111100"
  enabled: true
```

---

## `jackery.update_plan`

All fields except `plan_id` are optional. Only the fields you provide will be updated.

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `days` | No | string | 7-character day mask, Monday through Sunday |
| `enabled` | No | boolean | Enable or disable the plan |
| `end_time` | No | string | End time in `HH:MM` format |
| `plan_id` | Yes | string | The plan ID (`pid`) to update |
| `start_time` | No | string | Start time in `HH:MM` format |
| `type` | No | integer | `1` = Charge, `2` = Discharge |

### Example

```yaml
service: jackery.update_plan
data:
  plan_id: "1757967897"
  enabled: false
```

---

## `jackery.delete_plan`

| Field | Required | Type | Description |
|-------|----------|------|-------------|
| `plan_id` | Yes | string | The plan ID (`pid`) to delete |

### Example

```yaml
service: jackery.delete_plan
data:
  plan_id: "1757967897"
```
