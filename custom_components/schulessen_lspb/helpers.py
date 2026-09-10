"""Small pure helpers for picking relevant days out of the fetched menu plan."""
from __future__ import annotations

from datetime import date as date_cls
from datetime import datetime

from .api import MenuDay
from .const import DEFAULT_SWITCH_HOUR


def sorted_from(days: list[MenuDay], reference: date_cls | None = None) -> list[MenuDay]:
    """Return days sorted by date, optionally only those from `reference` onwards."""
    result = sorted(days, key=lambda d: d.the_date)
    if reference is not None:
        result = [d for d in result if d.the_date >= reference]
    return result


def today_entry(days: list[MenuDay]) -> MenuDay | None:
    today = date_cls.today()
    for day in days:
        if day.the_date == today:
            return day
    return None


def next_school_day(days: list[MenuDay], today: date_cls | None = None) -> MenuDay | None:
    """First day strictly after `today` that has any offers at all.

    This is the day you can still influence: ordering closes at 15:00 on the
    day before, so by the time "today" matters for a warning, today's own
    order is already locked in. The day worth checking (and warning about)
    is the next school day.
    """
    today = today or date_cls.today()
    for day in sorted_from(days, today):
        if day.the_date > today and day.has_offers:
            return day
    return None


def count_advance_orders(days: list[MenuDay], today: date_cls | None = None) -> int:
    """Number of days from today onwards that already have an order placed."""
    today = today or date_cls.today()
    return sum(1 for day in sorted_from(days, today) if day.has_offers and day.has_order)


def relevant_day(
    days: list[MenuDay], now: datetime | None = None, switch_hour: int = DEFAULT_SWITCH_HOUR
) -> MenuDay | None:
    """The day the "current meal" sensor should currently point at.

    Before `switch_hour`, that's today (if it has offers). From `switch_hour`
    onwards, it switches to the next school day - the day still worth
    checking/acting on before the 15:00 ordering cutoff.
    """
    now = now or datetime.now()
    if now.hour < switch_hour:
        day = today_entry(days)
        if day is not None and day.has_offers:
            return day
    return next_school_day(days, now.date())
