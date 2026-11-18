"""Sensory (rejestry + wartości wyliczane + licznik energii)."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

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
        if d.fn == "energy":
            entities.append(ThesllaEnergySensor(coordinator, d))
        elif d.fn and d.fn.startswith("meter_"):
            entities.append(ThesllaMeterSensor(coordinator, d))
        else:
            entities.append(ThesllaSensor(coordinator, d))
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
    """Odzyskana energia [kWh] (total_increasing – działa w panelu Energia)."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None:
            try:
                self.coordinator.restore_energy(float(last.state))
            except (ValueError, TypeError):
                pass

    def _state(self):
        return round(self.coordinator.energy_kwh, 3)

    def _has_data(self) -> bool:
        return True


def _period_start(period: str, now: datetime) -> datetime:
    base = now.replace(minute=0, second=0, microsecond=0)
    if period == "godzina":
        return base
    base = base.replace(hour=0)
    if period == "dzien":
        return base
    base = base.replace(day=1)
    if period == "miesiac":
        return base
    return base.replace(month=1)


class ThesllaMeterSensor(ThesllaSensor, RestoreEntity):
    """Licznik okresowy (godzina/dzień/miesiąc/rok) – odpowiednik utility_meter, zerowany na starcie okresu."""

    def __init__(self, coordinator: ThesllaCoordinator, definition: EntityDef) -> None:
        super().__init__(coordinator, definition)
        self._period = definition.fn.removeprefix("meter_")
        self._value = 0.0
        self._period_start = _period_start(self._period, dt_util.now())
        self._last_total: float | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is None:
            return
        try:
            stored_start = dt_util.parse_datetime(last.attributes.get("last_reset", ""))
            # wartość z bieżącego okresu przywracamy, z poprzedniego – nie (nie znamy energii z przerwy)
            if stored_start is not None and dt_util.as_local(stored_start) >= self._period_start:
                self._value = float(last.state)
        except (ValueError, TypeError):
            pass

    @property
    def last_reset(self) -> datetime:
        return self._period_start

    def _state(self):
        return round(self._value, 3)

    def _has_data(self) -> bool:
        return True

    @callback
    def _handle_coordinator_update(self) -> None:
        start = _period_start(self._period, dt_util.now())
        if start != self._period_start:  # zmiana okresu → zerowanie
            self._period_start = start
            self._value = 0.0
        total = self.coordinator.session_kwh  # niezależne od przywracania sensora energii
        if self._last_total is not None and total >= self._last_total:
            self._value += total - self._last_total
        self._last_total = total
        super()._handle_coordinator_update()
