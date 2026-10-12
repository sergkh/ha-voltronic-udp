"""Data coordinator for the Voltronic UDP integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import PipUdpClient, PipUdpError
from .const import DOMAIN


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
        try:
            return await self.hass.async_add_executor_job(self.client.read)
        except (OSError, PipUdpError) as err:
            raise UpdateFailed(f"Unable to read inverter: {err}") from err
