"""Binary sensory (coile)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ThesllaConfigEntry, ThesllaCoordinator
from .definitions import EntityDef
from .entity import ThesllaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ThesllaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ThesllaBinarySensor(coordinator, d)
        for d in coordinator.enabled_defs
        if d.platform == Platform.BINARY_SENSOR
    )


class ThesllaBinarySensor(ThesllaEntity, BinarySensorEntity):
    def __init__(self, coordinator: ThesllaCoordinator, definition: EntityDef) -> None:
        super().__init__(coordinator, definition)
        self._attr_device_class = definition.device_class

    def _state(self):
        v = self.coordinator.values.get(self._def.dp)
        return None if v is None else bool(v)

    @property
    def is_on(self) -> bool | None:
        return self._state()
