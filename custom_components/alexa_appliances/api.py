"""API client for Alexa Smart Home appliances."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiohttp import ClientSession, ClientTimeout

from .const import (
    ALEXA_HARDWARE_CAPABILITIES,
    ALEXA_HARDWARE_TYPES,
    GQL_SMART_HOME_QUERY,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

API_TIMEOUT = ClientTimeout(total=30)
CSRF_URLS = [
    "/api/language",
    "/spa/index.html",
    "/api/devices-v2/device?cached=false",
]


class AlexaApplianceApi:
    """Client for the undocumented Alexa Smart Home API."""

    def __init__(self, session: ClientSession, cookies: dict[str, str]) -> None:
        self._session = session
        self._cookies = cookies
        self._csrf: str | None = None
        self._base_url = "https://alexa.amazon.com"

    @property
    def _headers(self) -> dict[str, str]:
        cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        if self._csrf:
            cookie_str += f"; csrf={self._csrf}"
        headers = {
            "Content-Type": "application/json",
            "Cookie": cookie_str,
            "User-Agent": USER_AGENT,
        }
        if self._csrf:
            headers["csrf"] = self._csrf
        return headers

    async def _ensure_csrf(self) -> None:
        """Fetch CSRF token if we don't have one."""
        if self._csrf:
            return
        cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        for url in CSRF_URLS:
            try:
                async with self._session.get(
                    f"{self._base_url}{url}",
                    headers={
                        "Cookie": cookie_str,
                        "User-Agent": USER_AGENT,
                    },
                    timeout=API_TIMEOUT,
                ) as resp:
                    for cookie in resp.cookies.values():
                        if cookie.key == "csrf":
                            self._csrf = cookie.value
                            _LOGGER.debug("CSRF token acquired from %s", url)
                            return
            except Exception:
                continue
        _LOGGER.warning("Could not acquire CSRF token")

    async def get_appliances(self) -> list[dict[str, Any]]:
        """Discover all smart home appliances (excluding Echo devices)."""
        await self._ensure_csrf()
        async with self._session.post(
            f"{self._base_url}/nexus/v1/graphql",
            json={"query": GQL_SMART_HOME_QUERY},
            headers=self._headers,
            timeout=API_TIMEOUT,
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
            if types & ALEXA_HARDWARE_TYPES:
                continue
            cap_interfaces = {
                c.get("interfaceName") for c in legacy.get("capabilities", [])
            }
            if cap_interfaces & ALEXA_HARDWARE_CAPABILITIES:
                continue
            appliances.append(legacy)

        _LOGGER.debug("Discovered %d non-Echo appliances", len(appliances))
        return appliances

    async def get_state(self, entity_id: str) -> list[dict[str, Any]]:
        """Get the current state of an appliance."""
        result = await self.get_states_batch([entity_id])
        return result.get(entity_id, [])

    async def get_states_batch(
        self, entity_ids: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """Get current state of multiple appliances in a single request."""
        payload = {
            "stateRequests": [
                {"entityId": eid, "entityType": "ENTITY"} for eid in entity_ids
            ]
        }
        async with self._session.post(
            f"{self._base_url}/api/phoenix/state",
            json=payload,
            headers=self._headers,
            timeout=API_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            data = await resp.json(content_type=None)

        result: dict[str, list[dict[str, Any]]] = {eid: [] for eid in entity_ids}
        for device_state in data.get("deviceStates", []):
            eid = device_state.get("entity", {}).get("entityId")
            if eid not in result:
                continue
            for raw in device_state.get("capabilityStates", []):
                result[eid].append(
                    json.loads(raw) if isinstance(raw, str) else raw
                )
        return result

    async def set_state(
        self, entity_id: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Send a control command to an appliance."""
        await self._ensure_csrf()
        payload = {
            "controlRequests": [
                {
                    "entityId": entity_id,
                    "entityType": "ENTITY",
                    "parameters": parameters,
                }
            ]
        }
        _LOGGER.debug("Control request: %s", payload)
        async with self._session.put(
            f"{self._base_url}/api/phoenix/state",
            json=payload,
            headers=self._headers,
            timeout=API_TIMEOUT,
        ) as resp:
            data = await resp.json(content_type=None)
            _LOGGER.debug("Control response (%s): %s", resp.status, data)
            resp.raise_for_status()
            errors = data.get("errors", [])
            if errors:
                err = errors[0]
                _LOGGER.warning(
                    "Control error for %s: %s - %s",
                    entity_id, err.get("code"), err.get("message"),
                )
            return data
