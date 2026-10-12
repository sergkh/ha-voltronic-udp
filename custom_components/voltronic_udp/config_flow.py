"""Configuration flow for the Voltronic UDP integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, OptionsFlowWithReload
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .client import PipUdpClient, PipUdpError
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_SOURCE_PORT,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_SOURCE_PORT,
    DOMAIN,
)


SCAN_INTERVAL_VALIDATOR = vol.All(vol.Coerce(int), vol.Range(min=5, max=3600))


def _schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST): str,
            vol.Optional(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): cv.port,
            vol.Optional(
                CONF_SOURCE_PORT,
                default=defaults.get(CONF_SOURCE_PORT, DEFAULT_SOURCE_PORT),
            ): cv.port,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
            ): SCAN_INTERVAL_VALIDATOR,
        }
    )


async def _async_probe(hass, data: dict[str, Any]) -> str:
    """Test a UDP PIP connection without blocking the event loop."""
    client = PipUdpClient(data[CONF_HOST], data[CONF_PORT], data[CONF_SOURCE_PORT])
    try:
        return await hass.async_add_executor_job(client.probe)
    finally:
        client.close()


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for a UDP PIP bridge."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> VoltronicOptionsFlow:
        """Create the options flow."""
        return VoltronicOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial setup form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                model = await _async_probe(self.hass, user_input)
            except (OSError, PipUdpError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"pip_udp_{user_input[CONF_HOST]}_{user_input[CONF_PORT]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Voltronic {model}", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema(), errors=errors)


class VoltronicOptionsFlow(OptionsFlowWithReload):
    """Change polling behavior without re-adding the inverter."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the optional poll interval."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): SCAN_INTERVAL_VALIDATOR,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
