"""Coordinator – odpytuje tylko rejestry potrzebne włączonym encjom, każdy w swoim interwale."""
from __future__ import annotations

import logging
import time
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    AIR_HEAT_CAPACITY,
    CONF_ENTITIES,
    DOMAIN,
    MAX_FLOW,
    MAX_READ_FAILS,
    TICK_SECONDS,
)
from .definitions import (
    DP,
    DP_BYPASS_ACT,
    DP_FLOW_EXTRACT,
    DP_FLOW_SUPPLY,
    DP_T_CZERPNIA,
    DP_T_NAWIEW,
    DP_T_WYWIEW,
    ENTITIES_BY_KEY,
    build_plan,
)
from .modbus_client import ThesllaConnectionError, ThesllaError, ThesllaModbusClient, ThesllaReadError

_LOGGER = logging.getLogger(__name__)

ThesllaConfigEntry = ConfigEntry["ThesllaCoordinator"]


class ThesllaCoordinator(DataUpdateCoordinator[None]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(seconds=TICK_SECONDS),
        )
        d = entry.data
        self.client = ThesllaModbusClient(d)
        self.enabled_defs = [ENTITIES_BY_KEY[k] for k in d.get(CONF_ENTITIES, []) if k in ENTITIES_BY_KEY]
        self._plan = build_plan(self.enabled_defs)
        self._due: dict[DP, float] = dict.fromkeys(self._plan, 0.0)
        self._fails: dict[DP, int] = dict.fromkeys(self._plan, 0)
        self.values: dict[DP, int | bool | None] = dict.fromkeys(self._plan)

    # ---------- odpytywanie ----------
    async def _async_update_data(self) -> None:
        now = time.monotonic()
        for dp in [dp for dp, due in self._due.items() if due <= now]:
            try:
                self.values[dp] = await self.client.async_read(*dp)
                self._fails[dp] = 0
            except ThesllaConnectionError as err:
                raise UpdateFailed(f"Brak połączenia z bramką Modbus: {err}") from err
            except ThesllaReadError as err:
                self._fails[dp] += 1
                _LOGGER.debug("Błąd odczytu %s: %s", dp, err)
                if self._fails[dp] >= MAX_READ_FAILS:
                    self.values[dp] = None
            self._due[dp] = time.monotonic() + self._plan[dp]

    async def async_write(self, dp: DP, value: int) -> None:
        try:
            await self.client.async_write(dp[0], dp[1], value)
            self.values[dp] = await self.client.async_read(*dp)
        except ThesllaError as err:
            raise HomeAssistantError(f"Zapis do rejestru {dp} nie powiódł się: {err}") from err
        self._due[dp] = time.monotonic() + self._plan[dp]
        self.async_update_listeners()

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
        await self.client.async_close()

    # ---------- wartości wyliczane ----------
    def _temp(self, dp: DP) -> float | None:
        v = self.values.get(dp)
        return None if v is None or v == -32768 else v * 0.1

    def calc_efficiency(self) -> float | None:
        bypass = self.values.get(DP_BYPASS_ACT)
        if bypass is None:
            return None
        if bypass:
            return 0.0
        t1, t2, t3 = self._temp(DP_T_CZERPNIA), self._temp(DP_T_NAWIEW), self._temp(DP_T_WYWIEW)
        if None in (t1, t2, t3):
            return None
        if abs(t3 - t1) < 0.1:
            return 0.0
        return round((t2 - t1) / (t3 - t1) * 100, 2)

    def _pct(self, dp: DP) -> float | None:
        v = self.values.get(dp)
        return None if v is None or v < 0 else round(v * 100 / MAX_FLOW, 2)

    def calc_flow_supply_pct(self) -> float | None:
        return self._pct(DP_FLOW_SUPPLY)

    def calc_flow_extract_pct(self) -> float | None:
        return self._pct(DP_FLOW_EXTRACT)

    def calc_power(self) -> float | None:
        bypass = self.values.get(DP_BYPASS_ACT)
        if bypass is None:
            return None
        if bypass:
            return 0.0
        tcz, tn = self._temp(DP_T_CZERPNIA), self._temp(DP_T_NAWIEW)
        flow = self.values.get(DP_FLOW_SUPPLY)
        if tcz is None or tn is None or flow is None or flow < 0:
            return None
        return round(abs((tn - tcz) * flow * AIR_HEAT_CAPACITY / 3600), 2)
