"""Sensor entities for the Schulessen integration."""
from __future__ import annotations

from datetime import date

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SWITCH_HOUR, DEFAULT_SWITCH_HOUR, DOMAIN
from .helpers import count_advance_orders, next_school_day, relevant_day, sorted_from


def _day_to_dict(day) -> dict:
    return {
        "date": day.the_date.isoformat(),
        "weekday": day.weekday,
        "has_order": day.has_order,
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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SchulessenOrderedTodaySensor(coordinator, entry),
            SchulessenNextSchoolDaySensor(coordinator, entry),
            SchulessenMenuplanSensor(coordinator, entry),
            SchulessenAdvanceOrdersSensor(coordinator, entry),
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
    """What's ordered for the currently relevant day.

    Before the configured switch hour (default 14:00) that's today; from
    then on it switches to the next school day, since ordering closes at
    15:00 the day before and today's order is already locked in by then.
    `date`/`weekday`/`is_today` are exposed as attributes (not baked into
    the state string) so a dashboard card can format them however it wants.
    """

    _attr_name = "Schulessen aktuelles Essen"
    _attr_icon = "mdi:food"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_ordered_today"

    def _switch_hour(self) -> int:
        return self._entry.options.get(CONF_SWITCH_HOUR, DEFAULT_SWITCH_HOUR)

    def _relevant_day(self):
        return relevant_day(self.coordinator.data or [], switch_hour=self._switch_hour())

    @property
    def native_value(self) -> str | None:
        day = self._relevant_day()
        if day is None:
            return None
        if not day.ordered_options:
            return "Nichts bestellt"
        return ", ".join(o.description for o in day.ordered_options)

    @property
    def extra_state_attributes(self) -> dict:
        day = self._relevant_day()
        if day is None:
            return {}
        attrs = _day_to_dict(day)
        attrs["is_today"] = day.the_date == date.today()
        return attrs


class SchulessenNextSchoolDaySensor(_BaseSchulessenSensor):
    """The next day with offers - the one you can still order/change.

    Ordering closes at 15:00 on the day before, so this is the day that
    actually matters for a "did I forget to order?" automation.
    """

    _attr_name = "Schulessen nächster Schultag"
    _attr_icon = "mdi:calendar-arrow-right"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_next_school_day"

    @property
    def native_value(self) -> str | None:
        day = next_school_day(self.coordinator.data or [])
        if day is None:
            return None
        if not day.ordered_options:
            return "Nichts bestellt"
        return ", ".join(o.description for o in day.ordered_options)

    @property
    def extra_state_attributes(self) -> dict:
        day = next_school_day(self.coordinator.data or [])
        return _day_to_dict(day) if day else {}


class SchulessenMenuplanSensor(_BaseSchulessenSensor):
    """Full forward-looking menu plan (current + next week) as an attribute list."""

    _attr_name = "Schulessen Menüplan"
    _attr_icon = "mdi:calendar-text"
    _attr_native_unit_of_measurement = "Tage"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_menuplan"

    @property
    def native_value(self) -> int:
        days = sorted_from(self.coordinator.data or [])
        return sum(1 for d in days if d.has_offers)

    @property
    def extra_state_attributes(self) -> dict:
        days = sorted_from(self.coordinator.data or [])
        return {"days": [_day_to_dict(d) for d in days if d.has_offers]}


class SchulessenAdvanceOrdersSensor(_BaseSchulessenSensor):
    """How many upcoming school days already have an order placed."""

    _attr_name = "Schulessen Bestellungen im Voraus"
    _attr_icon = "mdi:calendar-check"
    _attr_native_unit_of_measurement = "Tage"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_advance_orders"

    @property
    def native_value(self) -> int:
        return count_advance_orders(self.coordinator.data or [])
