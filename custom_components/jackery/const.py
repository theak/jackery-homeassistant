"""Constants for the Jackery integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)

# The domain of your integration. Should be unique.
DOMAIN = "jackery"

# Polling interval
POLLING_INTERVAL_SEC = 60

# Charging plan DP identifiers for Jackery Plus devices.
CHARGING_PLAN_SWITCH = "107"
CHARGING_PLAN_DATA = "108"

# Short descriptions shown as a 'description' attribute on each entity.
ENTITY_HELP_TEXT: dict[str, str] = {
    # Sensors
    "rb": "Current battery charge level across all connected packs.",
    "ddt": "Minimum battery % reserved for backup during power outages.",
    "bt": "Internal battery temperature.",
    "op": "Total power currently being drawn from the device.",
    "ip": "Total power input from all sources (AC, DC, solar).",
    "acip": "Power input from the AC wall connection.",
    "cip": "Power input from the DC/car port.",
    "acpsp": "Power input from connected solar panels.",
    "it": "Estimated time until battery is fully charged.",
    "ot": "Estimated remaining runtime at current draw.",
    "acov": "Voltage on the AC output bus.",
    "acov1": "Voltage measured at the AC outlet terminals.",
    "acohz": "Frequency of the AC output waveform.",
    "ec": "Device error code.",
    "bs": "Battery state: Idle, Charging, Discharging, or Fault.",
    "bi": "Whether an external battery pack is connected.",
    "uo": "Device timezone offset from UTC (converted to hours).",
    "pss": "Whether power is supplied by grid or station (batteries/solar).",
    "last_updated": "Timestamp of the last successful data poll from Jackery API.",
    "cloud_online": "Whether the Jackery cloud currently reports this device as connected.",
    "cloud_offline_time": "When the Jackery cloud last saw this device disconnect.",
    "cloud_online_time": "When the Jackery cloud last saw this device connect.",
    "ds": "Total solar energy generated.",
    "dh": "Total household energy consumed.",
    "de": "Total battery energy discharged.",
    "dg": "Total grid energy consumed.",
    # Fault sensors (Transfer Switch)
    "fz_gs": "Mains power connection status.",
    "fz_ec1": "AC1 energy storage error code.",
    "fz_ec2": "AC2 energy storage error code.",
    "fz_ta1": "AC1 temperature alarm.",
    "fz_ta2": "AC2 temperature alarm.",
    "fz_moc": "Module overload.",
    # Fault binary sensors (Transfer Switch)
    "fz_es": "Emergency stop button has been triggered.",
    "fz_bs1": "Communication lost with AC1.",
    "fz_bs2": "Communication lost with AC2.",
    "fz_ol": "Transfer Switch cover is open.",
    "fz_ntc": "NTC temperature sensor reading is abnormal.",
    "fz_rtc": "Real-time clock module fault.",
    # Battery slot sensors (Transfer Switch)
    "ac1_rb": "Battery level of the device connected to AC1.",
    "ac1_op": "Output power from the device connected to AC1.",
    "ac1_ip": "Input power to the device connected to AC1.",
    "ac1_ot": "Estimated remaining runtime for the device connected to AC1.",
    "ac1_it": "Estimated time until fully charged for the device connected to AC1.",
    "ac1_bs": "Battery state of the device connected to AC1.",
    "ac1_bi": "Whether a battery device is connected to AC1.",
    "ac1_bp_count": "Number of add-on battery packs connected to the AC1 device.",
    "ac1_acpsp": "Power input from solar panels connected to the AC1 device.",
    "ac1_ss": "Solar panel input type at AC1: None, High Voltage, Low Voltage, or both.",
    "ac1_trb": "Total remaining battery energy stored in the AC1 device.",
    "ac2_rb": "Battery level of the device connected to AC2.",
    "ac2_op": "Output power from the device connected to AC2.",
    "ac2_ip": "Input power to the device connected to AC2.",
    "ac2_ot": "Estimated remaining runtime for the device connected to AC2.",
    "ac2_it": "Estimated time until fully charged for the device connected to AC2.",
    "ac2_bs": "Battery state of the device connected to AC2.",
    "ac2_bi": "Whether a battery device is connected to AC2.",
    "ac2_bp_count": "Number of add-on battery packs connected to the AC2 device.",
    "ac2_acpsp": "Power input from solar panels connected to the AC2 device.",
    "ac2_ss": "Solar panel input type at AC2: None, High Voltage, Low Voltage, or both.",
    "ac2_trb": "Total remaining battery energy stored in the AC2 device.",
    **{f"{slot}_pack_{i}_rb": f"Battery level of add-on pack {i} connected to {slot.upper()}." for slot in ("ac1", "ac2") for i in range(1, 6)},
    # Explorer 5000 diagnostic sensors
    "ss": "Solar panel input type: None, High Voltage, Low Voltage, or both.",
    "pc": "Parallel connection mode: None, Charge, or Discharge.",
    # Binary sensors
    "box": "Whether this device is connected to a Smart Transfer Switch.",
    "acpss": "Whether AC power is being passed through to the output.",
    "oac": "Whether the AC outlet is currently outputting power.",
    "odc": "Whether the combined DC output (USB + car) is active.",
    "odcc": "Whether the DC car port is outputting power.",
    "odcu": "Whether the USB ports are outputting power.",
    "ta": "Device temperature has exceeded a warning threshold.",
    "tp": "Device has entered temperature protection mode and reduced output.",
    "pal": "Device power or protection alarm is active.",
    "ups": "UPS mode, provides ~20ms switchover from grid to battery on outage.",
    "pmb": "At least one output port is active.",
    # Switches
    "rc": "Forces the battery to charge from grid power regardless of mode or schedule.",
    "wps": "WiFi Protected Setup (WPS) button for quick WiFi network connection.",
    # Selects
    "en": "Automatic Charging keeps batteries full for power outages. Scheduled Tasks follows plans. Self Consumption prioritizes battery/solar.",
    "lm": "Controls the built-in LED light mode.",
    "cs": "Fast charges at full speed. Mute reduces fan noise at slower charge rate.",
    "lps": "Full uses 100% capacity. Eco limits to ~85% to extend battery lifespan.",
    # Numbers
    "ast": "Minutes of inactivity before the device powers off automatically.",
    "pm": "Minutes before the device enters energy saving (reduced standby draw).",
    "sltb": "Minutes before the screen turns off.",
    "autoDt": "Backup reserve % for Automatic Charging mode.",
    "cdsDt": "Backup reserve % for Scheduled Tasks mode.",
    "selfDt": "Backup reserve % for Self Consumption mode.",
    # Transfer Switch network diagnostics
    "wsig": "WiFi signal strength (RSSI) in dBm.",
    "wname": "SSID of the connected WiFi network.",
    "wip": "IP address assigned to the Transfer Switch.",
    "mac": "MAC address of the Transfer Switch WiFi interface.",
    # Portable per-port power sensors
    "oacPw": "AC outlet power draw (W).",
    "usba1": "USB-A port 1 power draw (W).",
    "usba2": "USB-A port 2 power draw (W).",
    "usba3": "USB-A port 3 power draw (W).",
    "usbc1": "USB-C port 1 power draw (W).",
    "usbc2": "USB-C port 2 power draw (W).",
    "usbc3": "USB-C port 3 power draw (W).",
    "cop": "Car (12V) output power (W).",
    "iacPw": "AC input power (W) - portable device variant (may be reported instead of acip).",
    "ipalPw": "Power received from parallel-connected devices (W).",
    "opalPw": "Power sent to parallel-connected devices (W).",
    "oac2": "Second AC outlet status.",
    # Portable diagnostic sensors
    "acps": "AC Power Status.",
    "iac": "Whether AC Input is Connected.",
    "idc": "Whether DC Input is Connected.",
    "wss": "WiFi Signal Status.",
    "tt": "Temperature Threshold.",
    "acmode": "AC Output Mode: Normal or Timer.",
    "accd": "AC Output Countdown remaining in seconds.",
    "odct": "DC Output Countdown remaining in seconds.",
    "odcut": "USB Output Countdown remaining in seconds.",
    "odcct": "DC Car Output Countdown remaining in seconds.",
    "oact": "AC Output Countdown remaining in seconds.",
    # Portable limit sensors
    "dt": "Portable Backup Reserve percentage.",
    "dl": "Discharge Limit percentage.",
    "cl": "Charge Limit percentage.",
    "bc": "Battery Cutoff percentage.",
    "odcPrioSoc": "DC Priority SOC Threshold percentage.",
    # Portable priority and memory controls
    "outPrio": "Whether AC Output Priority is enabled.",
    "odcPrio": "Whether DC Output Priority is enabled.",
    "dhg_recall": "Whether Discharge Memory restores the previous output state after startup.",
}

BATTERY_STATUS_LABELS: dict[int, str] = {
    0: "Idle",
    1: "Charging",
    2: "Discharging",
    3: "Fault",
}

GRID_STATUS_LABELS: dict[int,str] = {
    0: "Grid Power",
    1: "Station Power",
}

def _battery_status_value(value: object) -> str:
    """Return a friendly label for battery status codes."""
    try:
        status = int(value)
    except (TypeError, ValueError):
        return str(value)

    return BATTERY_STATUS_LABELS.get(status, str(value))

def _grid_status_value(value: object) -> str:
    """Return a friendly label for grid status codes."""
    try:
        status = int(value)
    except (TypeError, ValueError):
        return str(value)

    return GRID_STATUS_LABELS.get(status, str(value))

def _connected_value(value: object) -> str:
    """Return Yes/No for connection status."""
    try:
        return "Yes" if int(value) else "No"
    except (TypeError, ValueError):
        return str(value)

SOLAR_TYPE_LABELS: dict[int, str] = {
    0: "None",
    1: "High Voltage",
    2: "Low Voltage",
    3: "High & Low Voltage",
}

PARALLEL_CONNECTION_LABELS: dict[int, str] = {
    0: "None",
    1: "Charge",
    2: "Discharge",
}

AC_OUTPUT_MODE_LABELS: dict[int, str] = {
    0: "Normal",
    1: "Timer",
}

MAINS_FAULT_LABELS: dict[int, str] = {
    0: "OK",
    1: "Not Connected",
    2: "Abnormality",
}

TEMP_ALARM_LABELS: dict[int, str] = {
    0: "OK",
    1: "High Temperature",
    2: "Low Temperature",
}

MODULE_OVERLOAD_LABELS: dict[int, str] = {
    0: "OK",
    1: "Mains Power Overload",
    2: "Energy Storage Overload",
}

# Error code labels: F1-FF map to values 1-13
_EC_CODES = ["F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "FA", "FC", "FE", "FF"]
ERROR_CODE_LABELS: dict[int, str] = {0: "OK"}
ERROR_CODE_LABELS.update({i + 1: code for i, code in enumerate(_EC_CODES)})

def _fault_label(labels: dict[int, str]) -> Callable[[object], str]:
    """Return a value mapper for a fault field with known labels."""
    def _map(value: object) -> str:
        try:
            code = int(value)
        except (TypeError, ValueError):
            return str(value)
        return labels.get(code, str(value))
    return _map

@dataclass
class JackerySensorEntityDescription(SensorEntityDescription):
    """Describes a Jackery sensor entity."""

    value: Callable[[any], any] | None = None


# Sensor descriptions
# This defines all the sensors we'll create for each device.
SENSOR_DESCRIPTIONS: tuple[JackerySensorEntityDescription, ...] = (
    JackerySensorEntityDescription(
        key="rb",
        name="Remaining Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
    ),
    JackerySensorEntityDescription(
        key="bt",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="op",
        name="Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
    ),
    JackerySensorEntityDescription(
        key="ip",
        name="Total Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
    ),
    JackerySensorEntityDescription(
        key="acip",
        name="AC Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
    ),
    JackerySensorEntityDescription(
        key="cip",
        name="DC Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
    ),
    JackerySensorEntityDescription(
        key="acpsp",
        name="Solar Panel Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="it",
        name="Time to Full",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ot",
        name="Remaining Output Time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=None,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="acov",
        name="AC Output Voltage (Bus)",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="acov1",
        name="AC Output Voltage (Outlet)",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="acohz",
        name="AC Output Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ec",
        name="Error Code",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="bs",
        name="Battery Status",
        icon="mdi:battery-heart-variant",
        entity_category=None,
        value=_battery_status_value,
    ),
    JackerySensorEntityDescription(

        key="bi",
        name="Battery Connected",
        icon="mdi:battery-multiple",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="pss",
        name="Power System State",
        icon="mdi:transmission-tower",
        entity_category=None,
        value=_grid_status_value,
    ),
    JackerySensorEntityDescription(
        key="ss",
        name="Solar Type",
        icon="mdi:solar-power-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(SOLAR_TYPE_LABELS),
    ),
    JackerySensorEntityDescription(
        key="pc",
        name="Parallel Connection",
        icon="mdi:battery-sync",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(PARALLEL_CONNECTION_LABELS),
    ),
    JackerySensorEntityDescription(
        key="last_updated",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="cloud_offline_time",
        name="Last Offline",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:cloud-off-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="cloud_online_time",
        name="Last Online",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:cloud-check-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Energy counters (Transfer Switch)
    JackerySensorEntityDescription(
        key="ds",
        name="Solar Generation",
        native_unit_of_measurement="Wh",
        icon="mdi:solar-power-variant",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="dh",
        name="House Consumption",
        native_unit_of_measurement="Wh",
        icon="mdi:home-lightning-bolt",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="de",
        name="Battery Discharge",
        native_unit_of_measurement="Wh",
        icon="mdi:battery-arrow-down",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="dg",
        name="Grid Consumption",
        native_unit_of_measurement="Wh",
        icon="mdi:transmission-tower",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Fault sub-object fields with multiple states
    JackerySensorEntityDescription(
        key="fz_gs",
        name="Mains Power Fault",
        icon="mdi:transmission-tower",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(MAINS_FAULT_LABELS),
    ),
    JackerySensorEntityDescription(
        key="fz_ec1",
        name="AC1 Error Code",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(ERROR_CODE_LABELS),
    ),
    JackerySensorEntityDescription(
        key="fz_ec2",
        name="AC2 Error Code",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(ERROR_CODE_LABELS),
    ),
    JackerySensorEntityDescription(
        key="fz_ta1",
        name="AC1 Temperature Alarm",
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(TEMP_ALARM_LABELS),
    ),
    JackerySensorEntityDescription(
        key="fz_ta2",
        name="AC2 Temperature Alarm",
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(TEMP_ALARM_LABELS),
    ),
    JackerySensorEntityDescription(
        key="fz_moc",
        name="Module Overload",
        icon="mdi:flash-alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(MODULE_OVERLOAD_LABELS),
    ),
    # Battery slot sensors (Transfer Switch ac1/ac2 flattened)
    JackerySensorEntityDescription(
        key="ac1_rb",
        name="AC1 Battery Level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac1_op",
        name="AC1 Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac1_ip",
        name="AC1 Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac1_acpsp",
        name="AC1 Solar Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ac1_ot",
        name="AC1 Remaining Time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ac1_it",
        name="AC1 Time to Full",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ac1_bs",
        name="AC1 Battery Status",
        icon="mdi:battery-heart-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_battery_status_value,
    ),
    JackerySensorEntityDescription(
        key="ac1_bi",
        name="AC1 Connected",
        icon="mdi:battery-heart-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_connected_value,
    ),
    JackerySensorEntityDescription(
        key="ac2_rb",
        name="AC2 Battery Level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac2_op",
        name="AC2 Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac2_ip",
        name="AC2 Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac2_acpsp",
        name="AC2 Solar Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ac2_ot",
        name="AC2 Remaining Time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ac2_it",
        name="AC2 Time to Full",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ac2_bs",
        name="AC2 Battery Status",
        icon="mdi:battery-heart-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_battery_status_value,
    ),
    JackerySensorEntityDescription(
        key="ac2_bi",
        name="AC2 Connected",
        icon="mdi:battery-heart-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_connected_value,
    ),
    JackerySensorEntityDescription(
        key="ac1_bp_count",
        name="AC1 Battery Packs",
        icon="mdi:battery-plus-variant",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac2_bp_count",
        name="AC2 Battery Packs",
        icon="mdi:battery-plus-variant",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac1_ss",
        name="AC1 Solar Type",
        icon="mdi:solar-power-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(SOLAR_TYPE_LABELS),
    ),
    JackerySensorEntityDescription(
        key="ac1_trb",
        name="AC1 Total Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ac2_ss",
        name="AC2 Solar Type",
        icon="mdi:solar-power-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(SOLAR_TYPE_LABELS),
    ),
    JackerySensorEntityDescription(
        key="ac2_trb",
        name="AC2 Total Battery",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Transfer Switch network diagnostics
    JackerySensorEntityDescription(
        key="wsig",
        name="WiFi Signal Strength",
        native_unit_of_measurement="dBm",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="wname",
        name="WiFi Network Name",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="wip",
        name="WiFi IP Address",
        icon="mdi:ip",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="mac",
        name="MAC Address",
        icon="mdi:identifier",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Per-pack battery level sensors (up to 5 packs per slot)
    *[
        JackerySensorEntityDescription(
            key=f"{slot}_pack_{i}_rb",
            name=f"{slot.upper()} Pack {i} Battery",
            native_unit_of_measurement=PERCENTAGE,
            device_class=SensorDeviceClass.BATTERY,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        )
        for slot in ("ac1", "ac2")
        for i in range(1, 6)
    ],
    # Portable per-port power sensors
    JackerySensorEntityDescription(
        key="oacPw",
        name="AC Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="usba1",
        name="USB-A Port 1 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="usba2",
        name="USB-A Port 2 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="usba3",
        name="USB-A Port 3 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="usbc1",
        name="USB-C Port 1 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="usbc2",
        name="USB-C Port 2 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="usbc3",
        name="USB-C Port 3 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="cop",
        name="Car (12V) Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="iacPw",
        name="AC Input Power (Portable)",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="ipalPw",
        name="Parallel Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="opalPw",
        name="Parallel Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Portable diagnostic sensors
    JackerySensorEntityDescription(
        key="acps",
        name="AC Power Status",
        icon="mdi:power-plug-check",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="wss",
        name="WiFi Signal Status",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="tt",
        name="Temperature Threshold",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        icon="mdi:thermometer",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="acmode",
        name="AC Output Mode",
        icon="mdi:power-plug-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_fault_label(AC_OUTPUT_MODE_LABELS),
    ),
    JackerySensorEntityDescription(
        key="accd",
        name="AC Output Countdown",
        native_unit_of_measurement="s",
        icon="mdi:timer",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="odct",
        name="DC Output Countdown",
        native_unit_of_measurement="s",
        icon="mdi:timer",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="odcut",
        name="USB Output Countdown",
        native_unit_of_measurement="s",
        icon="mdi:timer",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="odcct",
        name="DC Car Output Countdown",
        native_unit_of_measurement="s",
        icon="mdi:timer",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="oact",
        name="AC Output Countdown",
        native_unit_of_measurement="s",
        icon="mdi:timer",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Portable limit sensors
    JackerySensorEntityDescription(
        key="dt",
        name="Portable Backup Reserve",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="dl",
        name="Discharge Limit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="cl",
        name="Charge Limit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="bc",
        name="Battery Cutoff",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="odcPrioSoc",
        name="DC Priority SOC Threshold",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

# Binary sensor descriptions
# These define all binary (ON/OFF) sensors for each device.
# Note: Different device models may emit different parameters:
# - odc: DC Output (for models with single DC toggle for USB + Car)
# - odcc: DC Car Output (for models with separate DC Car toggle)
# - odcu: USB Output (for models with separate USB toggle)
BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="cloud_online",
        name="Cloud Connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:cloud-sync-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="oac",
        name="AC Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug",
        entity_category=None,
    ),
    BinarySensorEntityDescription(
        key="odc",
        name="DC Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power",
        entity_category=None,
    ),
    BinarySensorEntityDescription(
        key="odcc",
        name="DC Car Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:car",
        entity_category=None,
    ),
    BinarySensorEntityDescription(
        key="odcu",
        name="USB Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:usb-port",
        entity_category=None,
    ),
    BinarySensorEntityDescription(
        key="ta",
        name="Temperature Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="tp",
        name="Temperature Protection",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="pal",
        name="Power Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-octagon-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="ups",
        name="UPS Mode",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug-battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="pmb",
        name="Outlets Active",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="box",
        name="Transfer Switch Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:transit-transfer",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="acpss",
        name="AC Pass-through",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Fault sub-object fields
    # Multi-state faults (gs, ec1, ec2, ta1, ta2, moc) are in SENSOR_DESCRIPTIONS.
    BinarySensorEntityDescription(
        key="fz_es",
        name="Emergency Stop",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-octagon",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="fz_bs1",
        name="AC1 Communication Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:battery-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="fz_bs2",
        name="AC2 Communication Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:battery-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="fz_ol",
        name="Cover Open",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:door-open",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="fz_ntc",
        name="Temperature Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:thermometer-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="fz_rtc",
        name="RTC Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:clock-alert-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # Portable binary sensors
    BinarySensorEntityDescription(
        key="oac2",
        name="Second AC Outlet",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug",
        entity_category=None,
    ),
    # Portable diagnostic sensors
    BinarySensorEntityDescription(
        key="iac",
        name="AC Input Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:power-plug",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    BinarySensorEntityDescription(
        key="idc",
        name="DC Input Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:car-battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)
