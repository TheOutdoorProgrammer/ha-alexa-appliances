"""API client for Alexa Smart Home appliances."""

from __future__ import annotations

import json
from typing import Any

from aiohttp import ClientSession

from .const import _LOGGER, ECHO_APPLIANCE_TYPES, GQL_SMART_HOME_QUERY, USER_AGENT


class AlexaApplianceApi:
    """Client for the undocumented Alexa Smart Home API."""

    def __init__(self, session: ClientSession, cookies: dict[str, str]) -> None:
        self._session = session
        self._cookies = cookies
        self._base_url = "https://alexa.amazon.com"

    @property
    def _headers(self) -> dict[str, str]:
        cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        return {
            "Content-Type": "application/json",
            "Cookie": cookie_str,
            "User-Agent": USER_AGENT,
        }

    async def get_appliances(self) -> list[dict[str, Any]]:
        """Discover all smart home appliances (excluding Echo devices)."""
        async with self._session.post(
            f"{self._base_url}/nexus/v1/graphql",
            json={"query": GQL_SMART_HOME_QUERY},
            headers=self._headers,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

        items = data.get("data", {}).get("endpoints", {}).get("items", [])
        appliances = []
        for item in items:
            legacy = item.get("legacyAppliance")
            if not legacy:
                continue
            types = set(legacy.get("applianceTypes", []))
            if types & ECHO_APPLIANCE_TYPES:
                continue
            appliances.append(legacy)

        _LOGGER.debug("Discovered %d non-Echo appliances", len(appliances))
        return appliances

    async def get_state(self, entity_id: str) -> list[dict[str, Any]]:
        """Get the current state of an appliance."""
        payload = {
            "stateRequests": [
                {"entityId": entity_id, "entityType": "ENTITY"},
            ]
        }
        async with self._session.post(
            f"{self._base_url}/api/phoenix/state",
            json=payload,
            headers=self._headers,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

        states = []
        for device_state in data.get("deviceStates", []):
            for raw in device_state.get("capabilityStates", []):
                states.append(json.loads(raw) if isinstance(raw, str) else raw)
        return states

    async def set_state(
        self, entity_id: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a control command to an appliance."""
        payload = {
            "controlRequests": [
                {
                    "entityId": entity_id,
                    "entityType": "ENTITY",
                    "parameters": parameters,
                }
            ]
        }
        async with self._session.put(
            f"{self._base_url}/api/phoenix/state",
            json=payload,
            headers=self._headers,
        ) as resp:
            resp.raise_for_status()
            return await resp.json(content_type=None)
