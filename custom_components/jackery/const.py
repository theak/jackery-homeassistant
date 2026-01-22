"""Constants for the Jackery integration."""

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
    PERCENTAGE,
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
        key="it",
        name="Time to Full",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda value: value / 100.0,
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
)

# Binary sensor descriptions
# These define all binary (ON/OFF) sensors for each device.
BINARY_SENSOR_DESCRIPTIONS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="oac",
        name="AC Output",
        device_class=BinarySensorDeviceClass.POWER,
        icon="mdi:power-plug",
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
)
