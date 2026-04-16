"""Select platform for Jackery."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator

from .api import JackeryAPI
from .const import DOMAIN
from .protocol import control_spec, supported_keys

SELECT_KEYS = ("lm", "cs", "lps")
SELECT_DESCRIPTIONS: dict[str, EntityDescription] = {
    key: EntityDescription(
        key=spec.key,
        name=spec.name,
        icon=spec.icon,
    )
    for key in SELECT_KEYS
    for spec in (control_spec(key),)
}
SELECT_OPTIONS: dict[str, tuple[str, ...]] = {
    key: control_spec(key).options for key in SELECT_KEYS
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Jackery select entities."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    api: JackeryAPI = entry_data["api"]
    coordinators: dict[str, DataUpdateCoordinator] = entry_data["coordinators"]
    devices: list[dict] = entry_data["devices"]

    entities = []
    for device in devices:
        device_id = device["devId"]
        coordinator = coordinators.get(device_id)
        device_sn = device.get("devSn")
        if coordinator is None or not device_sn:
            continue

        for key in supported_keys(coordinator.data, SELECT_KEYS):
            entities.append(
                JackerySelectEntity(
                    api=api,
                    coordinator=coordinator,
                    description=SELECT_DESCRIPTIONS[key],
                    device_info=device,
                )
            )

    async_add_entities(entities)


class JackerySelectEntity(CoordinatorEntity, SelectEntity):
    """Implementation of a Jackery select."""

    entity_description: EntityDescription

    def __init__(
        self,
        api: JackeryAPI,
        coordinator: DataUpdateCoordinator,
        description: EntityDescription,
        device_info: dict,
    ) -> None:
        """Initialize the select."""
        super().__init__(coordinator)
        self.entity_description = description
        self._api = api
        self._slug = control_spec(description.key).slug
        self._options = SELECT_OPTIONS[description.key]
        self._device_id = device_info["devId"]
        self._device_sn = device_info["devSn"]
        self._attr_unique_id = f"{self._device_id}_{description.key}"
        self._attr_icon = description.icon
        self._attr_options = list(self._options)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=device_info.get("devName", f"Jackery Device {self._device_id}"),
            manufacturer="Jackery",
            model=device_info.get("productType"),
        )

    @property
    def name(self) -> str:
        """Return the entity name."""
        return self.entity_description.name

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None

        try:
            return self._options[int(value)]
        except (IndexError, TypeError, ValueError):
            return None

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        if option not in self._options:
            raise HomeAssistantError(
                f"Unsupported option '{option}' for {self.entity_description.name}."
            )

        try:
            await self._api.async_set_device_property(
                self._device_id,
                self._device_sn,
                self._slug,
                option,
            )
        except Exception as err:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.name}: {err}"
            ) from err

        updated_data = dict(self.coordinator.data or {})
        updated_data[self.entity_description.key] = self._options.index(option)
        self.coordinator.async_set_updated_data(updated_data)
        await self.coordinator.async_request_refresh()
