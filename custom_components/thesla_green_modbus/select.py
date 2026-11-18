"""Listy wyboru: tryb specjalny, sezon, auto/manual."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
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
        ThesllaSelect(coordinator, d) for d in coordinator.enabled_defs if d.platform == Platform.SELECT
    )


class ThesllaSelect(ThesllaEntity, SelectEntity):
    def __init__(self, coordinator: ThesllaCoordinator, definition: EntityDef) -> None:
        super().__init__(coordinator, definition)
        self._by_label = {label: value for value, label in definition.options}
        self._by_value = {value: label for value, label in definition.options}
        self._all_labels = dict(definition.all_labels) or self._by_value
        self._attr_options = list(self._by_label)

    def _state(self):
        return self.coordinator.values.get(self._def.dp)  # surowa wartość rejestru

    @property
    def current_option(self) -> str | None:
        # wartości spoza listy (np. wietrzenie z czujnika) -> brak wybranej opcji, szczegóły w atrybutach
        return self._by_value.get(self._state())

    @property
    def extra_state_attributes(self) -> dict:
        raw = self._state()
        return {"wartosc_rejestru": raw, "aktualny_stan": self._all_labels.get(raw, str(raw))}

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_write(self._def.dp, self._by_label[option])
