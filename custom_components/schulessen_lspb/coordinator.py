"""Data update coordinator for the Schulessen integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MenuDay, SchulessenAuthError, SchulessenClient, SchulessenConnectionError

_LOGGER = logging.getLogger(__name__)

# Fetch the current week plus the next one so a "next school day" lookup
# never runs dry near the end of a week (e.g. Friday afternoon needs to see
# into next Monday).
WEEKS_TO_FETCH = 2


class SchulessenCoordinator(DataUpdateCoordinator[list[MenuDay]]):
    """Fetches the current and next week's menu plan on a schedule."""

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
            days: list[MenuDay] = []
            for week_index in range(WEEKS_TO_FETCH):
                days.extend(await self.client.get_menu_week(week_index))
            days.sort(key=lambda d: d.the_date)
            return days
        except SchulessenAuthError as err:
            raise UpdateFailed(f"Login fehlgeschlagen: {err}") from err
        except SchulessenConnectionError as err:
            raise UpdateFailed(f"Verbindung fehlgeschlagen: {err}") from err
