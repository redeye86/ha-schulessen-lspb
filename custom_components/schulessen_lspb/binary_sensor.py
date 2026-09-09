"""Binary sensor for the Schulessen integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .helpers import next_school_day


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SchulessenNichtBestelltBinarySensor(coordinator, entry)])


class SchulessenNichtBestelltBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """On when the next school day has offers but nothing has been ordered yet.

    Ordering closes at 15:00 on the day before, so the day worth warning
    about is the next school day, not today (today's order is already
    locked in by the time this matters).
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
        day = next_school_day(self.coordinator.data or [])
        if day is None:
            return False
        return not day.has_order

    @property
    def extra_state_attributes(self) -> dict:
        day = next_school_day(self.coordinator.data or [])
        if day is None:
            return {}
        return {"date": day.the_date.isoformat(), "weekday": day.weekday}
