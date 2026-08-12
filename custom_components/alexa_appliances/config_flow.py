"""Config flow for Alexa Appliances."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlexaApplianceApi, AlexaApplianceAuthError, build_session_cookies
from .const import ALEXA_DEVICES_DOMAIN, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class AlexaAppliancesOptionsFlow(OptionsFlow):
    """Options flow for Alexa Appliances."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            "scan_interval", DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("scan_interval", default=current): vol.All(
                        int, vol.Range(min=30, max=600)
                    ),
                }
            ),
        )


class AlexaAppliancesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow that discovers appliances using alexa_devices auth."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: Any,
    ) -> AlexaAppliancesOptionsFlow:
        return AlexaAppliancesOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        alexa_entries = self.hass.config_entries.async_entries(ALEXA_DEVICES_DOMAIN)
        if not alexa_entries:
            return self.async_abort(reason="alexa_devices_not_configured")

        alexa_entry = alexa_entries[0]
        login_data = alexa_entry.data.get("login_data", {})
        cookies = build_session_cookies(login_data)

        if not cookies:
            return self.async_abort(reason="alexa_devices_no_cookies")

        if user_input is not None:
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Alexa Appliances",
                data={"alexa_entry_id": alexa_entry.entry_id},
            )

        session = async_get_clientsession(self.hass)
        api = AlexaApplianceApi(session, cookies)

        try:
            appliances = await api.get_appliances()
        except Exception:
            _LOGGER.exception("Failed to discover appliances")
            errors["base"] = "cannot_connect"
            appliances = []

        if not appliances and not errors:
            errors["base"] = "no_appliances"

        appliance_names = [
            f"{a['friendlyName']} ({a['manufacturerName']})" for a in appliances
        ]
        description = "\n".join(f"- {name}" for name in appliance_names)
        _LOGGER.info("Discovered appliances:\n%s", description)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={"appliance_count": str(len(appliances))},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-read cookies from alexa_devices and verify Amazon accepts them."""
        errors: dict[str, str] = {}

        if user_input is not None:
            alexa_entries = self.hass.config_entries.async_entries(
                ALEXA_DEVICES_DOMAIN
            )
            if not alexa_entries:
                return self.async_abort(reason="alexa_devices_not_configured")

            alexa_entry = alexa_entries[0]
            cookies = build_session_cookies(alexa_entry.data.get("login_data", {}))
            if not cookies:
                return self.async_abort(reason="alexa_devices_no_cookies")

            api = AlexaApplianceApi(async_get_clientsession(self.hass), cookies)
            try:
                await api.get_appliances()
            except AlexaApplianceAuthError:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Failed to verify Alexa session")
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={"alexa_entry_id": alexa_entry.entry_id},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
            errors=errors,
        )
