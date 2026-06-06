"""Config flow for Alexa Appliances."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlexaApplianceApi
from .const import _LOGGER, ALEXA_DEVICES_DOMAIN, DOMAIN


class AlexaAppliancesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow that discovers appliances using alexa_devices auth."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        alexa_entries = self.hass.config_entries.async_entries(ALEXA_DEVICES_DOMAIN)
        if not alexa_entries:
            return self.async_abort(reason="alexa_devices_not_configured")

        alexa_entry = alexa_entries[0]
        login_data = alexa_entry.data.get("login_data", {})
        cookies = login_data.get("website_cookies", {})

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
