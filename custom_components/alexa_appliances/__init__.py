"""Alexa Appliances integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlexaApplianceApi
from .const import _LOGGER, ALEXA_DEVICES_DOMAIN
from .coordinator import AlexaAppliancesConfigEntry, AlexaAppliancesCoordinator

PLATFORMS = [Platform.SENSOR, Platform.SWITCH, Platform.SELECT, Platform.NUMBER]


async def async_setup_entry(
    hass: HomeAssistant, entry: AlexaAppliancesConfigEntry
) -> bool:
    alexa_entry_id = entry.data.get("alexa_entry_id")
    alexa_entry = hass.config_entries.async_get_entry(alexa_entry_id)
    if not alexa_entry:
        alexa_entries = hass.config_entries.async_entries(ALEXA_DEVICES_DOMAIN)
        if not alexa_entries:
            _LOGGER.error("alexa_devices integration not found")
            return False
        alexa_entry = alexa_entries[0]

    login_data = alexa_entry.data.get("login_data", {})
    cookies = login_data.get("website_cookies", {})
    if not cookies:
        _LOGGER.error("No cookies found in alexa_devices config entry")
        return False

    session = async_get_clientsession(hass)
    api = AlexaApplianceApi(session, cookies)

    appliances = await api.get_appliances()
    _LOGGER.info("Found %d Alexa appliances", len(appliances))

    coordinator = AlexaAppliancesCoordinator(hass, entry, api, appliances)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: AlexaAppliancesConfigEntry
) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
