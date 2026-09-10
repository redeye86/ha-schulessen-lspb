"""Config flow for the Schulessen (OPC WebApp) integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import SchulessenAuthError, SchulessenClient, SchulessenConnectionError
from .const import (
    CONF_BASE_URL,
    CONF_KARTENNUMMER,
    CONF_MANDANT,
    CONF_SWITCH_HOUR,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL_MINUTES,
    DEFAULT_SWITCH_HOUR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_KARTENNUMMER): str,
        vol.Required("passwort"): str,
        vol.Optional(CONF_BASE_URL, default=DEFAULT_BASE_URL): str,
        vol.Optional(CONF_MANDANT): str,
    }
)


class SchulessenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = SchulessenClient(
                session=session,
                base_url=user_input[CONF_BASE_URL],
                kartennummer=user_input[CONF_KARTENNUMMER],
                passwort=user_input["passwort"],
                mandant=user_input.get(CONF_MANDANT) or None,
            )
            try:
                await client.login()
            except SchulessenAuthError:
                errors["base"] = "invalid_auth"
            except SchulessenConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unerwarteter Fehler beim Login")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(f"{user_input[CONF_BASE_URL]}_{user_input[CONF_KARTENNUMMER]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Schulessen", data=user_input)

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "SchulessenOptionsFlow":
        return SchulessenOptionsFlow(config_entry)


class SchulessenOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self._config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL_MINUTES)
        current_switch_hour = self._config_entry.options.get(CONF_SWITCH_HOUR, DEFAULT_SWITCH_HOUR)
        schema = vol.Schema(
            {
                vol.Optional("scan_interval", default=current_interval): int,
                vol.Optional(CONF_SWITCH_HOUR, default=current_switch_hour): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=23)
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
