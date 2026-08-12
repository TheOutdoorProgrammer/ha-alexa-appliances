"""API client for Alexa Smart Home appliances."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    ALEXA_HARDWARE_CAPABILITIES,
    ALEXA_HARDWARE_TYPES,
    GQL_SMART_HOME_QUERY,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

API_TIMEOUT = ClientTimeout(total=30)
STATE_BATCH_SIZE = 20
CSRF_URLS = [
    "/api/language",
    "/spa/index.html",
    "/api/devices-v2/device?cached=false",
]


class AlexaApplianceAuthError(Exception):
    """Amazon no longer accepts the session cookies borrowed from alexa_devices."""


def build_session_cookies(login_data: dict[str, Any]) -> dict[str, str]:
    """Build the alexa.amazon.com cookie jar; website_cookies omits session-token."""
    cookies = dict(login_data.get("website_cookies") or {})
    store_cookie = (login_data.get("store_authentication_cookie") or {}).get("cookie")
    if store_cookie:
        cookies["session-token"] = store_cookie
    return cookies


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
        if self._csrf and "csrf" not in self._cookies:
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
        """Fetch a CSRF token, raising if Amazon no longer accepts our session.

        Redirects stay unfollowed so an expired session surfaces as a 302.
        """
        if self._csrf:
            return
        if jar_csrf := self._cookies.get("csrf"):
            self._csrf = jar_csrf
            _LOGGER.debug("CSRF token taken from the stored cookie jar")
            return
        cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        attempts: list[str] = []
        statuses: list[int] = []
        for url in CSRF_URLS:
            try:
                async with self._session.get(
                    f"{self._base_url}{url}",
                    headers={
                        "Cookie": cookie_str,
                        "User-Agent": USER_AGENT,
                    },
                    timeout=API_TIMEOUT,
                    allow_redirects=False,
                ) as resp:
                    for cookie in resp.cookies.values():
                        if cookie.key == "csrf":
                            self._csrf = cookie.value
                            _LOGGER.debug("CSRF token acquired from %s", url)
                            return
                    statuses.append(resp.status)
                    attempts.append(f"{url} -> HTTP {resp.status}, no csrf cookie")
            except (ClientError, TimeoutError) as err:
                attempts.append(f"{url} -> {err!r}")
        if statuses and all(status == 200 for status in statuses):
            _LOGGER.debug(
                "No csrf cookie issued but the session is accepted; reads do not "
                "need one, so continuing without it"
            )
            return
        raise AlexaApplianceAuthError(
            "No CSRF token: it was absent from the stored cookie jar and none of "
            "the bootstrap URLs issued one. A 200 here means the session IS "
            "accepted and Amazon simply moved the token; a 302 or 401 means the "
            f"session is dead. Tried: {'; '.join(attempts)}. "
            f"Cookie names held: {sorted(self._cookies)}"
        )

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
        """Get appliance state in concurrent chunks; 76 in one request neared the 30s timeout."""
        await self._ensure_csrf()
        chunks = [
            entity_ids[i : i + STATE_BATCH_SIZE]
            for i in range(0, len(entity_ids), STATE_BATCH_SIZE)
        ]
        merged: dict[str, list[dict[str, Any]]] = {eid: [] for eid in entity_ids}
        for chunk_result in await asyncio.gather(
            *(self._fetch_state_chunk(chunk) for chunk in chunks)
        ):
            merged.update(chunk_result)
        return merged

    async def _fetch_state_chunk(
        self, entity_ids: list[str]
    ) -> dict[str, list[dict[str, Any]]]:
        """Fetch appliance state for one chunk of entity ids."""
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
        if not self._csrf:
            raise AlexaApplianceAuthError(
                "Control requires a CSRF token and Amazon did not issue one; "
                "state reads still work without it"
            )
        payload = {
            "controlRequests": [
                {
                    "entityId": entity_id,
                    "entityType": "APPLIANCE",
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
