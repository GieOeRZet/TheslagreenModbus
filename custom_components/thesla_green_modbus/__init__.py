"""Integracja Thesla Green ModBUS – rekuperator jako jedno urządzenie."""
from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import CONF_ENTITIES
from .coordinator import ThesllaConfigEntry, ThesllaCoordinator

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.NUMBER,
]


async def async_setup_entry(hass: HomeAssistant, entry: ThesllaConfigEntry) -> bool:
    coordinator = ThesllaCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    # usuń z rejestru encje, które użytkownik odznaczył w rekonfiguracji
    enabled = set(entry.data.get(CONF_ENTITIES, []))
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"
    for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if reg_entry.unique_id.startswith(prefix) and reg_entry.unique_id[len(prefix):] not in enabled:
            registry.async_remove(reg_entry.entity_id)

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ThesllaConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded
