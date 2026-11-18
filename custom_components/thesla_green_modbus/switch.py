"""Przełączniki (zapis do rejestrów holding)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import ThesllaConfigEntry
from .entity import ThesllaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ThesllaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ThesllaSwitch(coordinator, d) for d in coordinator.enabled_defs if d.platform == Platform.SWITCH
    )


class ThesllaSwitch(ThesllaEntity, SwitchEntity):
    def _state(self):
        raw = self.coordinator.values.get(self._def.dp)
        if raw is None:
            return None
        if raw == self._def.on_value:
            return True
        if raw == self._def.off_value:
            return False
        return None

    def _has_data(self) -> bool:
        return self.coordinator.values.get(self._def.dp) is not None

    @property
    def is_on(self) -> bool | None:
        return self._state()

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_write(self._def.dp, self._def.on_value)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_write(self._def.dp, self._def.off_value)
