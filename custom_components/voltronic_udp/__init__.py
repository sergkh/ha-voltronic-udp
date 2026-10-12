"""Set up the Voltronic UDP integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .client import PipUdpClient
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SOURCE_PORT,
    DEFAULT_RETRIES,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import VoltronicCoordinator

VoltronicConfigEntry = ConfigEntry[VoltronicCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VoltronicConfigEntry) -> bool:
    """Set up Voltronic UDP from a configuration entry."""
    client = PipUdpClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_SOURCE_PORT],
        DEFAULT_RETRIES,
    )
    scan_interval = entry.options.get(
        CONF_SCAN_INTERVAL,
        entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
    )
    coordinator = VoltronicCoordinator(hass, client, scan_interval)
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        client.close()
        raise ConfigEntryNotReady(f"Unable to connect to inverter: {err}") from err

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VoltronicConfigEntry) -> bool:
    """Unload a Voltronic UDP configuration entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.client.close()
    return unloaded
