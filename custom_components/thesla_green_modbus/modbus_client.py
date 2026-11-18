"""Klient Modbus: TCP, RTU over TCP, UDP i szeregowy (RTU/ASCII) – pymodbus."""
from __future__ import annotations

import asyncio
import inspect
import logging
from collections.abc import Mapping
from typing import Any

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient, AsyncModbusUdpClient
from pymodbus.exceptions import ConnectionException, ModbusException

from .const import (
    CONF_BAUDRATE,
    CONF_BYTESIZE,
    CONF_DELAY,
    CONF_HOST,
    CONF_METHOD,
    CONF_MSG_WAIT,
    CONF_PARITY,
    CONF_PORT,
    CONF_SERIAL_PORT,
    CONF_SLAVE,
    CONF_STOPBITS,
    CONF_TIMEOUT,
    CONF_TYPE,
    DEFAULT_BAUDRATE,
    DEFAULT_BYTESIZE,
    DEFAULT_METHOD,
    DEFAULT_MSG_WAIT_NETWORK,
    DEFAULT_MSG_WAIT_SERIAL,
    DEFAULT_PARITY,
    DEFAULT_STOPBITS,
    TYPE_RTUOVERTCP,
    TYPE_SERIAL,
    TYPE_UDP,
)

try:  # pymodbus >= 3.7
    from pymodbus.framer import FramerType

    F_RTU, F_SOCKET, F_ASCII = FramerType.RTU, FramerType.SOCKET, FramerType.ASCII
except ImportError:  # pymodbus 3.6.x
    from pymodbus.framer import ModbusAsciiFramer as F_ASCII  # type: ignore[no-redef]
    from pymodbus.framer import ModbusRtuFramer as F_RTU  # type: ignore[no-redef]
    from pymodbus.framer import ModbusSocketFramer as F_SOCKET  # type: ignore[no-redef]

_LOGGER = logging.getLogger(__name__)

# wartości w konfiguracji są małymi literami (wymóg tłumaczeń HA); pymodbus oczekuje N/E/O
PARITY_MAP = {"none": "N", "even": "E", "odd": "O", "N": "N", "E": "E", "O": "O"}


class ThesllaError(Exception):
    """Bazowy błąd."""


class ThesllaConnectionError(ThesllaError):
    """Brak połączenia z bramką / portem."""


class ThesllaReadError(ThesllaError):
    """Urządzenie nie odpowiedziało / zwróciło błąd dla danego rejestru."""


class ThesllaModbusClient:
    """Klient z jedną blokadą – wszystkie zapytania idą po kolei."""

    def __init__(self, conn: Mapping[str, Any]) -> None:
        self._conn = dict(conn)
        self._type = self._conn.get(CONF_TYPE, TYPE_RTUOVERTCP)  # starsze wpisy = rtuovertcp
        self._slave = int(self._conn[CONF_SLAVE])
        self._timeout = int(self._conn[CONF_TIMEOUT])
        self._delay = int(self._conn.get(CONF_DELAY, 0))
        default_wait = DEFAULT_MSG_WAIT_SERIAL if self._type == TYPE_SERIAL else DEFAULT_MSG_WAIT_NETWORK
        self._wait = int(self._conn.get(CONF_MSG_WAIT, default_wait)) / 1000
        self._lock = asyncio.Lock()
        self._client = None
        self._unit_kw = "slave"
        self._bit_method: dict[int, str] = {}

    # ---------- tworzenie klienta ----------
    def _create_client(self):
        c = self._conn
        try:
            if self._type == TYPE_SERIAL:
                framer = F_ASCII if c.get(CONF_METHOD, DEFAULT_METHOD) == "ascii" else F_RTU
                return AsyncModbusSerialClient(
                    c[CONF_SERIAL_PORT],
                    framer=framer,
                    baudrate=int(c.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)),
                    bytesize=int(c.get(CONF_BYTESIZE, DEFAULT_BYTESIZE)),
                    parity=PARITY_MAP.get(str(c.get(CONF_PARITY, DEFAULT_PARITY)), "E"),
                    stopbits=int(c.get(CONF_STOPBITS, DEFAULT_STOPBITS)),
                    timeout=self._timeout,
                    retries=1,
                )
            framer = F_RTU if self._type == TYPE_RTUOVERTCP else F_SOCKET
            cls = AsyncModbusUdpClient if self._type == TYPE_UDP else AsyncModbusTcpClient
            return cls(
                c[CONF_HOST], port=int(c[CONF_PORT]), framer=framer, timeout=self._timeout, retries=1
            )
        except (ImportError, RuntimeError) as err:
            raise ThesllaConnectionError(f"Nie można utworzyć klienta {self._type}: {err}") from err

    async def _ensure_connected(self) -> None:
        if self._client is None:
            self._client = self._create_client()
            params = inspect.signature(self._client.read_holding_registers).parameters
            self._unit_kw = "device_id" if "device_id" in params else "slave"
        if self._client.connected:
            return
        try:
            ok = await asyncio.wait_for(self._client.connect(), timeout=self._timeout + 1)
        except (OSError, asyncio.TimeoutError, ModbusException) as err:
            raise ThesllaConnectionError(str(err) or "connect failed") from err
        if not ok or not self._client.connected:
            raise ThesllaConnectionError("connect failed")
        if self._delay:  # opóźnienie po połączeniu (część urządzeń tego wymaga)
            await asyncio.sleep(self._delay)

    async def _request(self, method: str, address: int, **kwargs):
        async with self._lock:
            await self._ensure_connected()
            func = getattr(self._client, method)
            try:
                rr = await func(address, **kwargs, **{self._unit_kw: self._slave})
            except (ConnectionException, OSError) as err:
                self._client.close()
                raise ThesllaConnectionError(str(err)) from err
            except (ModbusException, asyncio.TimeoutError) as err:
                raise ThesllaReadError(str(err) or "no response") from err
            finally:
                if self._wait:  # przerwa między zapytaniami (message_wait_milliseconds)
                    await asyncio.sleep(self._wait)
        if rr.isError():
            raise ThesllaReadError(str(rr))
        return rr

    # ---------- odczyt / zapis ----------
    async def async_read(self, kind: str, address: int) -> int | bool:
        """Odczyt pojedynczego rejestru. kind: input | holding | coil."""
        if kind == "coil":
            return await self._read_bit(address)
        method = "read_input_registers" if kind == "input" else "read_holding_registers"
        rr = await self._request(method, address, count=1)
        if not rr.registers:
            raise ThesllaReadError(f"{method} {address}: empty response")
        value = rr.registers[0]
        return value - 65536 if value > 32767 else value  # int16

    async def _read_bit(self, address: int) -> bool:
        """Bit: najpierw coil (fn 1), w razie błędu/pustej odpowiedzi discrete input (fn 2)."""
        methods = ["read_coils", "read_discrete_inputs"]
        if (cached := self._bit_method.get(address)) is not None:
            methods = [cached]
        last: ThesllaReadError | None = None
        for method in methods:
            try:
                rr = await self._request(method, address, count=1)
            except ThesllaReadError as err:
                last = err
                continue
            if rr.bits:
                self._bit_method[address] = method
                return bool(rr.bits[0])
            last = ThesllaReadError(f"{method} {address}: empty response")
        raise last or ThesllaReadError("bit read failed")

    async def async_write(self, kind: str, address: int, value: int | bool) -> None:
        if kind == "coil":
            await self._request("write_coil", address, value=bool(value))
        else:
            await self._request("write_register", address, value=int(value) & 0xFFFF)

    async def async_close(self) -> None:
        if self._client is None:
            return
        result = self._client.close()
        if inspect.isawaitable(result):
            await result
