"""Sensor entities for the Schulessen integration."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorEntity
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
    async_add_entities(
        [
            SchulessenOrderedTodaySensor(coordinator, entry),
            SchulessenAvailableTodaySensor(coordinator, entry),
        ]
    )


class _BaseSchulessenSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Schulessen",
            manufacturer="OPC AG",
        )


class SchulessenOrderedTodaySensor(_BaseSchulessenSensor):
    """Shows what has actually been ordered for today."""

    _attr_name = "Schulessen bestellt (heute)"
    _attr_icon = "mdi:food"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_ordered_today"

    @property
    def native_value(self) -> str | None:
        day = _today_entry(self.coordinator.data or [])
        if day is None or not day.ordered_options:
            return "Nichts bestellt"
        return ", ".join(o.description for o in day.ordered_options)

    @property
    def extra_state_attributes(self) -> dict:
        day = _today_entry(self.coordinator.data or [])
        if day is None:
            return {}
        return {
            "date": day.the_date.isoformat(),
            "weekday": day.weekday,
            "ordered_options": [
                {"column": o.column, "description": o.description, "price": o.price}
                for o in day.ordered_options
            ],
        }


class SchulessenAvailableTodaySensor(_BaseSchulessenSensor):
    """Shows how many options are available today."""

    _attr_name = "Schulessen verfügbar (heute)"
    _attr_icon = "mdi:silverware-fork-knife"
    _attr_native_unit_of_measurement = "Gerichte"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_available_today"

    @property
    def native_value(self) -> int:
        day = _today_entry(self.coordinator.data or [])
        return len(day.options) if day else 0

    @property
    def extra_state_attributes(self) -> dict:
        day = _today_entry(self.coordinator.data or [])
        if day is None:
            return {}
        return {
            "date": day.the_date.isoformat(),
            "weekday": day.weekday,
            "options": [
                {
                    "column": o.column,
                    "description": o.description,
                    "price": o.price,
                    "ordered": o.ordered,
                }
                for o in day.options
            ],
        }
