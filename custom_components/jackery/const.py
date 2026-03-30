"""Constants for the Jackery integration."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntityDescription
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)

# The domain of your integration. Should be unique.
DOMAIN = "jackery"

# Polling interval
POLLING_INTERVAL_SEC = 60


@dataclass
class JackerySensorEntityDescription(SensorEntityDescription):
    """Describes a Jackery sensor entity."""

    value: Callable[[any], any] | None = None


@dataclass
class JackerySelectEntityDescription(SelectEntityDescription):
    """Describes a Jackery select entity."""


# Shared configuration entity ranges.
SETTING_MAX_VALUE = 999


# Sensor descriptions
SENSOR_DESCRIPTIONS: tuple[JackerySensorEntityDescription, ...] = (
    JackerySensorEntityDescription(
        key="rb",
        name="Remaining Battery",
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
        name="Input Power",
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
        name="Car Input Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
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
        key="acohz",
        name="AC Output Frequency",
        native_unit_of_measurement="Hz",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
    ),
    JackerySensorEntityDescription(
        key="ec",
        name="Error Code",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    JackerySensorEntityDescription(
        key="last_updated",
        name="Last Updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

# Binary sensor descriptions
BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="ta",
        name="Temperature Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer-alert",
    ),
    BinarySensorEntityDescription(
        key="pal",
        name="Power Alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert",
    ),
    BinarySensorEntityDescription(
        key="wss",
        name="Wireless Charging",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:charging-wireless",
    ),
)

SWITCH_DESCRIPTIONS: tuple[SwitchEntityDescription, ...] = (
    SwitchEntityDescription(
        key="oac",
        name="AC Output",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:power-plug",
    ),
    SwitchEntityDescription(
        key="odc",
        name="DC Output",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:power",
    ),
    SwitchEntityDescription(
        key="odcu",
        name="USB Output",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:usb-port",
    ),
    SwitchEntityDescription(
        key="odcc",
        name="DC Car Output",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:car",
    ),
    SwitchEntityDescription(
        key="iac",
        name="AC Input",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:transmission-tower-import",
    ),
    SwitchEntityDescription(
        key="idc",
        name="DC Input",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:current-dc",
    ),
    SwitchEntityDescription(
        key="sfc",
        name="Super Fast Charge",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:lightning-bolt",
        entity_category=EntityCategory.CONFIG,
    ),
    SwitchEntityDescription(
        key="ups",
        name="UPS Mode",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:power-plug-battery",
        entity_category=EntityCategory.CONFIG,
    ),
)

SELECT_DESCRIPTIONS: tuple[JackerySelectEntityDescription, ...] = (
    JackerySelectEntityDescription(
        key="lm",
        name="Light Mode",
        options=["off", "low", "high", "sos"],
        icon="mdi:lightbulb",
    ),
    JackerySelectEntityDescription(
        key="cs",
        name="Charge Speed",
        options=["fast", "mute"],
        icon="mdi:speedometer",
        entity_category=EntityCategory.CONFIG,
    ),
    JackerySelectEntityDescription(
        key="lps",
        name="Battery Protection",
        options=["full", "eco"],
        icon="mdi:battery-heart-variant",
        entity_category=EntityCategory.CONFIG,
    ),
)

NUMBER_DESCRIPTIONS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key="ast",
        name="Auto Shutdown",
        icon="mdi:timer-off-outline",
        mode="box",
        native_min_value=0,
        native_max_value=SETTING_MAX_VALUE,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="pm",
        name="Energy Saving",
        icon="mdi:leaf",
        mode="box",
        native_min_value=0,
        native_max_value=SETTING_MAX_VALUE,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
    ),
    NumberEntityDescription(
        key="sltb",
        name="Screen Timeout",
        icon="mdi:monitor-lock",
        mode="box",
        native_min_value=0,
        native_max_value=SETTING_MAX_VALUE,
        native_step=1,
        entity_category=EntityCategory.CONFIG,
    ),
)
