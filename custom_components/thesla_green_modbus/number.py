"""Suwak intensywności manualnej – ruszenie suwaka przełącza centralę na tryb manualny."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
        ThesllaNumber(coordinator, d) for d in coordinator.enabled_defs if d.platform == Platform.NUMBER
    )


class ThesllaNumber(ThesllaEntity, NumberEntity):
    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator: ThesllaCoordinator, definition: EntityDef) -> None:
        super().__init__(coordinator, definition)
        self._attr_native_min_value = definition.min_value
        self._attr_native_max_value = definition.max_value
        self._attr_native_step = definition.step
        self._attr_native_unit_of_measurement = definition.unit

    def _state(self):
        return self.coordinator.values.get(self._def.dp)

    @property
    def native_value(self) -> float | None:
        return self._state()

    async def async_set_native_value(self, value: float) -> None:
        # najpierw nastawa, potem przełączenie na manual – centrala nie skoczy na starą wartość
        await self.coordinator.async_write(self._def.dp, int(value))
        for dp, target in self._def.side_writes:
            if self.coordinator.values.get(dp) != target:
                await self.coordinator.async_write(dp, target)
