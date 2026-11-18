"""Wspólna baza encji."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_NAME, DOMAIN
from .coordinator import ThesllaCoordinator
from .definitions import EntityDef


class ThesllaEntity(CoordinatorEntity[ThesllaCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: ThesllaCoordinator, definition: EntityDef) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._def = definition
        self._snapshot: object = None
        self._attr_unique_id = f"{entry.entry_id}_{definition.key}"
        self._attr_name = definition.name
        self._attr_entity_category = definition.category
        if definition.icon:
            self._attr_icon = definition.icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_NAME],
            manufacturer="Thesla Green",
            model="Rekuperator (Modbus)",
        )

    def _state(self):
        raise NotImplementedError

    def _has_data(self) -> bool:
        return self._state() is not None

    @property
    def available(self) -> bool:
        return super().available and self._has_data()

    @callback
    def _handle_coordinator_update(self) -> None:
        # koordynator tyka co sekundę – zapisuj stan tylko gdy coś się zmieniło
        snapshot = (self.available, self._state())
        if snapshot == self._snapshot:
            return
        self._snapshot = snapshot
        self.async_write_ha_state()
