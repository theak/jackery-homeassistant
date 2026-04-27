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
    ),
    JackerySensorEntityDescription(
        key="ddt",
        name="Backup Reserve",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JackerySensorEntityDescription(
        key="bt",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="op",
        name="Output Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JackerySensorEntityDescription(
        key="ip",
        name="Total Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JackerySensorEntityDescription(
        key="acip",
        name="AC Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JackerySensorEntityDescription(
        key="cip",
        name="DC Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    JackerySensorEntityDescription(
        key="acpsp",
        name="Solar Panel Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="it",
        name="Time to Full",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="ot",
        name="Remaining Output Time",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="acov",
        name="AC Output Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="acov1",
        name="AC Outlet Output Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda value: value / 10.0,
    ),
    JackerySensorEntityDescription(
        key="acohz",
        name="AC Output Frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
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
        value=_battery_status_value,
    ),
    JackerySensorEntityDescription(
        key="bp",
        name="Battery Pack",
        icon="mdi:battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="bi",
        name="Batteries Indicated",
        icon="mdi:battery-multiple",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="uo",
        name="UTC Offset",
        native_unit_of_measurement=UnitOfTime.HOURS,
        icon="mdi:clock-time-four-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda value: value / 3600.0,
    ),
    JackerySensorEntityDescription(
        key="pss",
        name="Power System State",
        icon="mdi:transmission-tower",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=_grid_status_value
    ),
    JackerySensorEntityDescription(
        key="last_updated",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
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
        key="oac",
        name="AC Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug",
    ),
    BinarySensorEntityDescription(
        key="odc",
        name="DC Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power",
    ),
    BinarySensorEntityDescription(
        key="odcc",
        name="DC Car Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:car",
    ),
    BinarySensorEntityDescription(
        key="odcu",
        name="USB Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:usb-port",
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
    ),
    BinarySensorEntityDescription(
        key="pmb",
        name="Outlets Active",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)
