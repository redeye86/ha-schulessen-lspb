"""API client for the OPC WebApp school meal ordering system.

This talks to the same backend used by e.g. https://schulessen-bestellung.lspb.de/
(product "OPC WebApp" by OPC AG, used by many German municipalities under
different domains). The menu plan itself is only available as a server-rendered
HTML fragment embedded in a JSON response, so it has to be scraped.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime

from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

PRICE_RE = re.compile(r"(\d+,\d{2})\s*€")
DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")


class SchulessenAuthError(Exception):
    """Raised when login fails."""


class SchulessenConnectionError(Exception):
    """Raised when the API can't be reached or returns an unexpected response."""


@dataclass
class MenuOption:
    """A single offer (e.g. 'Menü 2') on a given day."""

    column: str
    description: str
    price: str | None
    ordered: bool
    angebot_id: str | None


@dataclass
class MenuDay:
    """All offers for a single day."""

    the_date: date
    weekday: str
    options: list[MenuOption] = field(default_factory=list)

    @property
    def ordered_options(self) -> list[MenuOption]:
        return [o for o in self.options if o.ordered]

    @property
    def has_offers(self) -> bool:
        return len(self.options) > 0

    @property
    def has_order(self) -> bool:
        return len(self.ordered_options) > 0


class SchulessenClient:
    """Thin async client around the OPC WebApp REST/HTML API."""

    def __init__(self, session, base_url: str, kartennummer: str, passwort: str, mandant: str | None = None) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._kartennummer = kartennummer
        self._passwort = passwort
        self._mandant = mandant
        self._logged_in = False

    async def _get_csrf_token(self) -> str:
        async with self._session.get(self._base_url + "/login") as resp:
            await resp.text()
        for cookie in self._session.cookie_jar.filter_cookies(self._base_url):
            if cookie.key.upper() == "XSRF-TOKEN":
                return cookie.value
        raise SchulessenConnectionError("XSRF-TOKEN cookie not set by server")

    async def login(self) -> None:
        """Authenticate and establish a session."""
        token = await self._get_csrf_token()

        payload = {
            "username": self._kartennummer,
            "password": self._passwort,
            "rememberMe": "1",
        }
        if self._mandant:
            payload["mandantOverride"] = self._mandant

        headers = {
            "X-CSRF-Token": token,
            "X-Requested-With": "XMLHttpRequest",
        }

        async with self._session.post(
            self._base_url + "/api/login/authenticate", json=payload, headers=headers
        ) as resp:
            if resp.status == 401 or resp.status == 403:
                raise SchulessenAuthError("Login abgelehnt (falsche Kartennummer/Passwort?)")
            if resp.status != 200:
                raise SchulessenConnectionError(f"Unerwarteter Status beim Login: {resp.status}")

        self._logged_in = True

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.login()

    async def get_menu_week(self, week_index: int = 0, retry: bool = True) -> list[MenuDay]:
        """Fetch and parse the menu plan for the given week (0 = current week)."""
        await self._ensure_login()

        url = f"{self._base_url}/api/menuplan/init/{week_index}"
        async with self._session.get(url) as resp:
            if resp.status in (401, 403) and retry:
                self._logged_in = False
                return await self.get_menu_week(week_index, retry=False)
            if resp.status != 200:
                raise SchulessenConnectionError(f"Unerwarteter Status beim Laden des Menüplans: {resp.status}")
            data = await resp.json(content_type=None)

        html = data.get("html_tablebody", "")
        if not html:
            raise SchulessenConnectionError("Antwort enthielt keinen Menüplan (html_tablebody fehlt)")
        return self._parse_tablebody(html)

    @staticmethod
    def _parse_tablebody(html: str) -> list[MenuDay]:
        soup = BeautifulSoup(html, "html.parser")
        days: list[MenuDay] = []

        for row in soup.find_all("tr"):
            date_cell = row.find("td", class_="MPDatum")
            if date_cell is None:
                continue

            date_match = DATE_RE.search(date_cell.get_text(" ", strip=True))
            if not date_match:
                continue
            the_date = datetime.strptime(date_match.group(1), "%d.%m.%Y").date()
            weekday_text = date_cell.get_text(" ", strip=True).replace(date_match.group(1), "").strip()

            day = MenuDay(the_date=the_date, weekday=weekday_text)

            for cell in row.find_all("td", class_="menu-td"):
                text_el = cell.find(class_="angebot-text")
                if text_el is None:
                    continue
                description = text_el.get_text(" ", strip=True)
                if not description:
                    continue

                column_el = cell.find(class_="angebot-spalte-name")
                column = column_el.get_text(strip=True) if column_el else ""

                price_match = PRICE_RE.search(cell.get_text(" ", strip=True))
                price = price_match.group(1) + " €" if price_match else None

                ordered = "angebot_bestellt" in (cell.get("class") or [])
                angebot_id = cell.get("data-angebot-id")

                day.options.append(
                    MenuOption(
                        column=column,
                        description=description,
                        price=price,
                        ordered=ordered,
                        angebot_id=angebot_id,
                    )
                )

            days.append(day)

        return days
