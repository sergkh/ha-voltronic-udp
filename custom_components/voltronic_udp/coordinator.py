"""Data coordinator for the Voltronic UDP integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import PipUdpClient, PipUdpError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VoltronicCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch live inverter data in Home Assistant's executor."""

    def __init__(self, hass: HomeAssistant, client: PipUdpClient, scan_interval: int) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Read the inverter, recreating its UDP socket once if needed."""
        try:
            return await self.hass.async_add_executor_job(self.client.read)
        except (OSError, PipUdpError) as err:
            _LOGGER.debug("Inverter read failed; recreating the UDP socket once: %s", err)
            try:
                await self.hass.async_add_executor_job(self.client.reconnect)
                return await self.hass.async_add_executor_job(self.client.read)
            except (OSError, PipUdpError) as retry_err:
                raise UpdateFailed(
                    f"Unable to read inverter after recreating UDP socket: {retry_err}"
                ) from retry_err
