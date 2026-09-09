"""API client for the OPC WebApp school meal ordering system.

This talks to the same backend used by e.g. https://schulessen-bestellung.lspb.de/
(product "OPC WebApp" by OPC AG, used by many German municipalities under
different domains). The menu plan itself is only available as a server-rendered
HTML fragment embedded in a JSON response, so it has to be scraped.
"""
from __future__ import annotations

import logging
import re
import ssl
from dataclasses import dataclass, field
from datetime import date, datetime

from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

PRICE_RE = re.compile(r"(\d+,\d{2})\s*€")
DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{4})")

# "angebot_bestellt" marks a still-editable ordered item; once the ordering
# deadline (15:00 the day before) passes, the same item switches to
# "angebot_bestnoedit" (bestellt, nicht editierbar) instead. Both mean
# "this was ordered".
ORDERED_CLASSES = {"angebot_bestellt", "angebot_bestnoedit"}

# Some OPC WebApp deployments (e.g. schulessen-bestellung.lspb.de) serve only
# the leaf certificate without the intermediate CA. Browsers paper over this
# by fetching the missing link via the certificate's AIA extension; Python's
# ssl module does not. Rather than disabling verification, we add the known,
# long-lived Starfield intermediate as an extra trust anchor so full chain
# verification still succeeds. Harmless no-op for servers that already send
# a complete chain.
_STARFIELD_G2_INTERMEDIATE = """-----BEGIN CERTIFICATE-----
MIIFADCCA+igAwIBAgIBBzANBgkqhkiG9w0BAQsFADCBjzELMAkGA1UEBhMCVVMx
EDAOBgNVBAgTB0FyaXpvbmExEzARBgNVBAcTClNjb3R0c2RhbGUxJTAjBgNVBAoT
HFN0YXJmaWVsZCBUZWNobm9sb2dpZXMsIEluYy4xMjAwBgNVBAMTKVN0YXJmaWVs
ZCBSb290IENlcnRpZmljYXRlIEF1dGhvcml0eSAtIEcyMB4XDTExMDUwMzA3MDAw
MFoXDTMxMDUwMzA3MDAwMFowgcYxCzAJBgNVBAYTAlVTMRAwDgYDVQQIEwdBcml6
b25hMRMwEQYDVQQHEwpTY290dHNkYWxlMSUwIwYDVQQKExxTdGFyZmllbGQgVGVj
aG5vbG9naWVzLCBJbmMuMTMwMQYDVQQLEypodHRwOi8vY2VydHMuc3RhcmZpZWxk
dGVjaC5jb20vcmVwb3NpdG9yeS8xNDAyBgNVBAMTK1N0YXJmaWVsZCBTZWN1cmUg
Q2VydGlmaWNhdGUgQXV0aG9yaXR5IC0gRzIwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQDlkGZL7PlGcakgg77pbL9KyUhpgXVObST2yxcT+LBxWYR6ayuF
pDS1FuXLzOlBcCykLtb6Mn3hqN6UEKwxwcDYav9ZJ6t21vwLdGu4p64/xFT0tDFE
3ZNWjKRMXpuJyySDm+JXfbfYEh/JhW300YDxUJuHrtQLEAX7J7oobRfpDtZNuTlV
Bv8KJAV+L8YdcmzUiymMV33a2etmGtNPp99/UsQwxaXJDgLFU793OGgGJMNmyDd+
MB5FcSM1/5DYKp2N57CSTTx/KgqT3M0WRmX3YISLdkuRJ3MUkuDq7o8W6o0OPnYX
v32JgIBEQ+ct4EMJddo26K3biTr1XRKOIwSDAgMBAAGjggEsMIIBKDAPBgNVHRMB
Af8EBTADAQH/MA4GA1UdDwEB/wQEAwIBBjAdBgNVHQ4EFgQUJUWBaFAmOD07LSy+
zWrZtj2zZmMwHwYDVR0jBBgwFoAUfAwyH6fZMH/EfWijYqihzqsHWycwOgYIKwYB
BQUHAQEELjAsMCoGCCsGAQUFBzABhh5odHRwOi8vb2NzcC5zdGFyZmllbGR0ZWNo
LmNvbS8wOwYDVR0fBDQwMjAwoC6gLIYqaHR0cDovL2NybC5zdGFyZmllbGR0ZWNo
LmNvbS9zZnJvb3QtZzIuY3JsMEwGA1UdIARFMEMwQQYEVR0gADA5MDcGCCsGAQUF
BwIBFitodHRwczovL2NlcnRzLnN0YXJmaWVsZHRlY2guY29tL3JlcG9zaXRvcnkv
MA0GCSqGSIb3DQEBCwUAA4IBAQBWZcr+8z8KqJOLGMfeQ2kTNCC+Tl94qGuc22pN
QdvBE+zcMQAiXvcAngzgNGU0+bE6TkjIEoGIXFs+CFN69xpk37hQYcxTUUApS8L0
rjpf5MqtJsxOYUPl/VemN3DOQyuwlMOS6eFfqhBJt2nk4NAfZKQrzR9voPiEJBjO
eT2pkb9UGBOJmVQRDVXFJgt5T1ocbvlj2xSApAer+rKluYjdkf5lO6Sjeb6JTeHQ
sPTIFwwKlhR8Cbds4cLYVdQYoKpBaXAko7nv6VrcPuuUSvC33l8Odvr7+2kDRUBQ
7nIMpBKGgc0T0U7EPMpODdIm8QC3tKai4W56gf0wrHofx1l7
-----END CERTIFICATE-----
"""


def _build_ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.load_verify_locations(cadata=_STARFIELD_G2_INTERMEDIATE)
    return context


_SSL_CONTEXT = _build_ssl_context()


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
        async with self._session.get(self._base_url + "/login", ssl=_SSL_CONTEXT) as resp:
            await resp.text()
        cookies = self._session.cookie_jar.filter_cookies(self._base_url)
        for name, morsel in cookies.items():
            if name.upper() == "XSRF-TOKEN":
                return morsel.value
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
            self._base_url + "/api/login/authenticate", json=payload, headers=headers, ssl=_SSL_CONTEXT
        ) as resp:
            if resp.status == 200:
                self._logged_in = True
                return

            try:
                error_data = await resp.json(content_type=None)
                message = error_data.get("errorMessage") or str(resp.status)
            except Exception:  # noqa: BLE001
                message = str(resp.status)

            if resp.status in (400, 401, 403):
                raise SchulessenAuthError(f"Login abgelehnt: {message}")
            raise SchulessenConnectionError(f"Unerwarteter Status beim Login: {resp.status} ({message})")

    async def _ensure_login(self) -> None:
        if not self._logged_in:
            await self.login()

    async def get_menu_week(self, week_index: int = 0, retry: bool = True) -> list[MenuDay]:
        """Fetch and parse the menu plan for the given week (0 = current week)."""
        await self._ensure_login()

        url = f"{self._base_url}/api/menuplan/init/{week_index}"
        async with self._session.get(url, ssl=_SSL_CONTEXT) as resp:
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

                ordered = bool(ORDERED_CLASSES & set(cell.get("class") or []))
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
