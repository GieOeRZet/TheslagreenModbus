"""Konfigurator: typ połączenia → parametry → wybór encji. Rekonfiguracja używa tych samych kroków."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_DELAY,
    CONF_ENTITIES,
    CONF_HOST,
    CONF_METHOD,
    CONF_MSG_WAIT,
    CONF_NAME,
    CONF_PARITY,
    CONF_PORT,
    CONF_SERIAL_PORT,
    CONF_SLAVE,
    CONF_STOPBITS,
    CONF_TIMEOUT,
    CONF_TYPE,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_DELAY,
    DEFAULT_HOST,
    DEFAULT_METHOD,
    DEFAULT_MSG_WAIT_NETWORK,
    DEFAULT_MSG_WAIT_SERIAL,
    DEFAULT_NAME,
    DEFAULT_PARITY,
    DEFAULT_PORT,
    DEFAULT_SLAVE,
    DEFAULT_STOPBITS,
    DEFAULT_TIMEOUT,
    DOMAIN,
    NETWORK_TYPES,
    TYPE_RTUOVERTCP,
    TYPE_SERIAL,
    TYPE_TCP,
    TYPE_UDP,
)
from .definitions import ALL_KEYS, ENTITY_DEFS, PLATFORM_LABEL
from .modbus_client import ThesllaConnectionError, ThesllaModbusClient, ThesllaReadError

INT_KEYS = (CONF_PORT, CONF_TIMEOUT, CONF_DELAY, CONF_MSG_WAIT, CONF_SLAVE, CONF_BAUDRATE, CONF_BYTESIZE, CONF_STOPBITS)


def _slider(min_: int, max_: int, unit: str | None = None, step: int = 1) -> NumberSelector:
    """Suwak + pole tekstowe (w trybie SLIDER frontend pokazuje oba)."""
    config: dict[str, Any] = {"min": min_, "max": max_, "step": step, "mode": NumberSelectorMode.SLIDER}
    if unit:  # selektor nie akceptuje None
        config["unit_of_measurement"] = unit
    return NumberSelector(NumberSelectorConfig(**config))


def _dropdown(options: list[str], translation_key: str | None = None, custom: bool = False) -> SelectSelector:
    config: dict[str, Any] = {
        "options": options,
        "mode": SelectSelectorMode.DROPDOWN,
        "custom_value": custom,
    }
    if translation_key:  # selektor nie akceptuje None
        config["translation_key"] = translation_key
    return SelectSelector(SelectSelectorConfig(**config))


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    """NumberSelector oddaje float, a select tekst – zamień na int tam, gdzie trzeba."""
    out = dict(data)
    for key in INT_KEYS:
        if key in out and out[key] not in (None, ""):
            out[key] = int(float(out[key]))
    return out


def _conn_id(data: dict[str, Any]) -> tuple:
    if data.get(CONF_TYPE) == TYPE_SERIAL:
        return (TYPE_SERIAL, data.get(CONF_SERIAL_PORT), data.get(CONF_SLAVE))
    return ("net", data.get(CONF_HOST), data.get(CONF_PORT), data.get(CONF_SLAVE))


async def _list_serial_ports(hass: HomeAssistant) -> list[str]:
    try:
        from serial.tools import list_ports

        ports = await hass.async_add_executor_job(list_ports.comports)
        return sorted(p.device for p in ports)
    except Exception:  # noqa: BLE001 – brak pyserial / brak portów
        return []


async def _validate_connection(data: dict[str, Any]) -> str | None:
    client = ThesllaModbusClient(data)
    try:
        await client.async_read("input", 16)  # temperatura czerpni – rejestr zawsze istnieje
    except ThesllaConnectionError:
        return "cannot_connect"
    except ThesllaReadError:
        return "no_response"
    finally:
        await client.async_close()
    return None


def _entities_schema(selected: list[str]) -> vol.Schema:
    options = {d.key: f"{d.name} ({PLATFORM_LABEL[d.platform]})" for d in ENTITY_DEFS}
    return vol.Schema({vol.Required(CONF_ENTITIES, default=selected): cv.multi_select(options)})


class ThesllaConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._prev: dict[str, Any] = {}

    @property
    def _reconfiguring(self) -> bool:
        return self.source == SOURCE_RECONFIGURE

    def _is_duplicate(self, data: dict[str, Any]) -> bool:
        exclude = self._get_reconfigure_entry().entry_id if self._reconfiguring else None
        new_id = _conn_id(data)
        for entry in self._async_current_entries():
            if entry.entry_id != exclude and _conn_id(dict(entry.data) | {CONF_TYPE: entry.data.get(CONF_TYPE, TYPE_RTUOVERTCP)}) == new_id:
                return True
        return False

    # ---------- krok 1: nazwa + typ połączenia ----------
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._data = {CONF_NAME: user_input[CONF_NAME], CONF_TYPE: user_input[CONF_TYPE]}
            return await self.async_step_connection()
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_TYPE, default=TYPE_RTUOVERTCP): _dropdown(
                    [TYPE_TCP, TYPE_RTUOVERTCP, TYPE_UDP, TYPE_SERIAL], "connection_type"
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry = self._get_reconfigure_entry()
        self._prev = dict(entry.data)
        if user_input is not None:
            self._data = {CONF_NAME: entry.data[CONF_NAME], CONF_TYPE: user_input[CONF_TYPE]}
            return await self.async_step_connection()
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TYPE, default=entry.data.get(CONF_TYPE, TYPE_RTUOVERTCP)
                ): _dropdown([TYPE_TCP, TYPE_RTUOVERTCP, TYPE_UDP, TYPE_SERIAL], "connection_type")
            }
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema)

    # ---------- krok 2: parametry zależne od typu ----------
    async def async_step_connection(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        overrides: dict[str, Any] = {}
        if user_input is not None:
            data = {**self._data, **_normalize(user_input)}
            overrides = data
            if self._is_duplicate(data):
                errors["base"] = "already_configured"
            elif error := await _validate_connection(data):
                errors["base"] = error
            else:
                self._data = data
                return await self.async_step_entities()

        conn_type = self._data[CONF_TYPE]
        serial = conn_type == TYPE_SERIAL

        def get(key: str, fallback: Any) -> Any:
            return overrides.get(key, self._prev.get(key, fallback))

        fields: dict[Any, Any] = {}
        if serial:
            ports = await _list_serial_ports(self.hass)
            current_port = get(CONF_SERIAL_PORT, ports[0] if ports else "/dev/ttyUSB0")
            fields[vol.Required(CONF_SERIAL_PORT, default=current_port)] = (
                _dropdown(ports, custom=True) if ports else TextSelector()
            )
            fields[vol.Required(CONF_BAUDRATE, default=str(get(CONF_BAUDRATE, DEFAULT_BAUDRATE)))] = _dropdown(
                ["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"], custom=True
            )
            fields[vol.Required(CONF_BYTESIZE, default=str(get(CONF_BYTESIZE, DEFAULT_BYTESIZE)))] = _dropdown(
                ["5", "6", "7", "8"]
            )
            fields[vol.Required(CONF_PARITY, default=get(CONF_PARITY, DEFAULT_PARITY))] = _dropdown(
                ["none", "even", "odd"], "parity"
            )
            fields[vol.Required(CONF_STOPBITS, default=str(get(CONF_STOPBITS, DEFAULT_STOPBITS)))] = _dropdown(
                ["1", "2"]
            )
            fields[vol.Required(CONF_METHOD, default=get(CONF_METHOD, DEFAULT_METHOD))] = _dropdown(
                ["rtu", "ascii"], "method"
            )
        else:
            fields[vol.Required(CONF_HOST, default=get(CONF_HOST, DEFAULT_HOST))] = str
            fields[vol.Required(CONF_PORT, default=get(CONF_PORT, DEFAULT_PORT))] = NumberSelector(
                NumberSelectorConfig(min=1, max=65535, step=1, mode=NumberSelectorMode.BOX)
            )

        # parametry wspólne (niezależne od typu połączenia – wg dokumentacji HA)
        same_type = self._prev.get(CONF_TYPE, TYPE_RTUOVERTCP) == conn_type
        default_wait = DEFAULT_MSG_WAIT_SERIAL if serial else DEFAULT_MSG_WAIT_NETWORK
        wait = overrides.get(CONF_MSG_WAIT, self._prev.get(CONF_MSG_WAIT, default_wait) if same_type else default_wait)
        fields[vol.Required(CONF_TIMEOUT, default=get(CONF_TIMEOUT, DEFAULT_TIMEOUT))] = _slider(1, 60, "s")
        fields[vol.Required(CONF_DELAY, default=get(CONF_DELAY, DEFAULT_DELAY))] = _slider(0, 30, "s")
        fields[vol.Required(CONF_MSG_WAIT, default=wait)] = _slider(0, 1000, "ms", step=5)
        fields[vol.Required(CONF_SLAVE, default=get(CONF_SLAVE, DEFAULT_SLAVE))] = _slider(1, 247)

        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema(fields),
            errors=errors,
            description_placeholders={"type": conn_type},
        )

    # ---------- krok 3: wybór encji ----------
    async def async_step_entities(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            data = {**self._data, CONF_ENTITIES: user_input[CONF_ENTITIES]}
            if self._reconfiguring:
                return self.async_update_reload_and_abort(self._get_reconfigure_entry(), data=data)
            return self.async_create_entry(title=data[CONF_NAME], data=data)
        if self._reconfiguring:
            current = [k for k in self._prev.get(CONF_ENTITIES, ALL_KEYS) if k in ALL_KEYS]
        else:
            current = list(ALL_KEYS)
        return self.async_show_form(step_id="entities", data_schema=_entities_schema(current))
