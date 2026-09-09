"""Data update coordinator for the Schulessen integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MenuDay, SchulessenAuthError, SchulessenClient, SchulessenConnectionError

_LOGGER = logging.getLogger(__name__)


class SchulessenCoordinator(DataUpdateCoordinator[list[MenuDay]]):
    """Fetches the current week's menu plan on a schedule."""

    def __init__(self, hass: HomeAssistant, client: SchulessenClient, update_interval_minutes: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="schulessen_lspb",
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client

    async def _async_update_data(self) -> list[MenuDay]:
        try:
            return await self.client.get_menu_week(0)
        except SchulessenAuthError as err:
            raise UpdateFailed(f"Login fehlgeschlagen: {err}") from err
        except SchulessenConnectionError as err:
            raise UpdateFailed(f"Verbindung fehlgeschlagen: {err}") from err
