"""The Schulessen (OPC WebApp) integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SchulessenClient
from .const import CONF_BASE_URL, CONF_KARTENNUMMER, CONF_MANDANT, DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN
from .coordinator import SchulessenCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

SERVICE_REFRESH = "refresh"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = SchulessenClient(
        session=session,
        base_url=entry.data[CONF_BASE_URL],
        kartennummer=entry.data[CONF_KARTENNUMMER],
        passwort=entry.data["passwort"],
        mandant=entry.data.get(CONF_MANDANT),
    )

    scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL_MINUTES)
    coordinator = SchulessenCoordinator(hass, client, scan_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    if not hass.services.has_service(DOMAIN, SERVICE_REFRESH):

        async def _async_handle_refresh(call: ServiceCall) -> None:
            """Force an immediate re-fetch of all configured Schulessen accounts."""
            for coordinator in hass.data.get(DOMAIN, {}).values():
                await coordinator.async_request_refresh()

        hass.services.async_register(DOMAIN, SERVICE_REFRESH, _async_handle_refresh)

    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_REFRESH)
    return unload_ok
