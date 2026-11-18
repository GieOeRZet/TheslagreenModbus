"""Sensory (rejestry + wartości wyliczane + licznik energii)."""
from __future__ import annotations

import time

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import ThesllaConfigEntry, ThesllaCoordinator
from .definitions import EntityDef
from .entity import ThesllaEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ThesllaConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities = []
    for d in coordinator.enabled_defs:
        if d.platform != Platform.SENSOR:
            continue
        entities.append(
            ThesllaEnergySensor(coordinator, d) if d.fn == "energy" else ThesllaSensor(coordinator, d)
        )
    async_add_entities(entities)


class ThesllaSensor(ThesllaEntity, SensorEntity):
    def __init__(self, coordinator: ThesllaCoordinator, definition: EntityDef) -> None:
        super().__init__(coordinator, definition)
        self._attr_native_unit_of_measurement = definition.unit
        self._attr_device_class = definition.device_class
        self._attr_state_class = definition.state_class
        if definition.precision is not None:
            self._attr_suggested_display_precision = definition.precision

    def _state(self):
        d = self._def
        if d.fn:
            return getattr(self.coordinator, f"calc_{d.fn}")()
        raw = self.coordinator.values.get(d.dp)
        if raw is None or (d.nan is not None and raw == d.nan):
            return None
        if d.scale == 1.0:
            return raw
        return round(raw * d.scale, d.precision if d.precision is not None else 1)

    @property
    def native_value(self):
        return self._state()


class ThesllaEnergySensor(ThesllaSensor, RestoreEntity):
    """Całkuje odzyskaną moc [W] do kWh (total_increasing – działa w panelu Energia)."""

    def __init__(self, coordinator: ThesllaCoordinator, definition: EntityDef) -> None:
        super().__init__(coordinator, definition)
        self._energy = 0.0
        self._last_ts: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            try:
                self._energy = float(last.state)
            except (ValueError, TypeError):
                self._energy = 0.0

    def _state(self):
        return round(self._energy, 3)

    def _has_data(self) -> bool:
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        now = time.monotonic()
        if self.coordinator.last_update_success:
            power = self.coordinator.calc_power()
            if power is not None and self._last_ts is not None:
                dt = now - self._last_ts
                if 0 < dt < 300:
                    self._energy += power * dt / 3_600_000  # W*s -> kWh
            self._last_ts = now
        else:
            self._last_ts = None
        super()._handle_coordinator_update()
