"""Data update coordinator for Alexa Appliances."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AlexaApplianceApi
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type AlexaAppliancesConfigEntry = ConfigEntry[AlexaAppliancesCoordinator]


class AlexaAppliancesCoordinator(
    DataUpdateCoordinator[dict[str, list[dict[str, Any]]]]
):
    """Coordinator that polls appliance states."""

    config_entry: AlexaAppliancesConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AlexaAppliancesConfigEntry,
        api: AlexaApplianceApi,
        appliances: list[dict[str, Any]],
    ) -> None:
        scan_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.api = api
        self.appliances = {a["entityId"]: a for a in appliances}

    async def _async_update_data(self) -> dict[str, list[dict[str, Any]]]:
        """Poll state for all tracked appliances in a single batch request."""
        try:
            return await self.api.get_states_batch(list(self.appliances.keys()))
        except Exception as err:
            raise UpdateFailed(
                f"Failed to get appliance states: {err}"
            ) from err

    def get_capability_value(
        self,
        alexa_entity_id: str,
        namespace: str,
        instance: str | None = None,
    ) -> Any | None:
        """Get a capability value from the last poll."""
        states = self.data.get(alexa_entity_id, []) if self.data else []
        for state in states:
            if state.get("namespace") != namespace:
                continue
            if instance is not None and state.get("instance") != instance:
                continue
            return state.get("value")
        return None
