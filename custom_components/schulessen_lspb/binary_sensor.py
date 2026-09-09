"""Binary sensor for the Schulessen integration."""
from __future__ import annotations

from datetime import date

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import MenuDay
from .const import DOMAIN


def _today_entry(days: list[MenuDay]) -> MenuDay | None:
    today = date.today()
    for day in days:
        if day.the_date == today:
            return day
    return None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SchulessenNichtBestelltBinarySensor(coordinator, entry)])


class SchulessenNichtBestelltBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """On when there are offers for today but nothing has been ordered.

    Intended to drive an automation that reminds you to order before it's
    too late. Off (no warning) on days with no offers at all, e.g. weekends
    or holidays.
    """

    _attr_name = "Schulessen nicht bestellt"
    _attr_icon = "mdi:alert"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_not_ordered"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Schulessen",
            manufacturer="OPC AG",
        )

    @property
    def is_on(self) -> bool | None:
        day = _today_entry(self.coordinator.data or [])
        if day is None or not day.has_offers:
            return False
        return not day.has_order

    @property
    def extra_state_attributes(self) -> dict:
        day = _today_entry(self.coordinator.data or [])
        if day is None:
            return {}
        return {"date": day.the_date.isoformat(), "weekday": day.weekday}
