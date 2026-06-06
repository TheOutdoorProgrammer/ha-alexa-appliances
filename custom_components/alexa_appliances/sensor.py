"""Sensor entities for Alexa Appliances."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AlexaAppliancesConfigEntry, AlexaAppliancesCoordinator
from .entity import AlexaApplianceEntity


def _mode_label(capability: dict[str, Any], value: str) -> str:
    """Resolve a mode value to its friendly name."""
    for mode in (
        capability.get("configuration", {}).get("supportedModes", [])
    ):
        if mode["value"] == value:
            names = mode.get("modeResources", {}).get("friendlyNames", [])
            if names:
                return names[0].get("value", {}).get("text", value)
    return value


class AlexaApplianceSensor(AlexaApplianceEntity, SensorEntity):
    """A read-only mode sensor (status, remaining time, etc.)."""

    def __init__(
        self,
        coordinator: AlexaAppliancesCoordinator,
        appliance: dict[str, Any],
        capability: dict[str, Any],
    ) -> None:
        instance = capability["instance"]
        super().__init__(
            coordinator, appliance, "Alexa.ModeController", instance
        )
        self._capability = capability
        friendly = (
            capability.get("resources", {}).get("friendlyNames", [{}])[0]
            .get("value", {})
            .get("text", f"Mode {instance}")
        )
        self._attr_translation_key = None
        self._attr_name = friendly
        self._mode_map: dict[str, str] = {}
        for mode in capability.get("configuration", {}).get("supportedModes", []):
            names = mode.get("modeResources", {}).get("friendlyNames", [])
            label = names[0]["value"]["text"] if names else mode["value"]
            self._mode_map[mode["value"]] = label

    @property
    def native_value(self) -> str | None:
        raw = self._capability_value
        if raw is None:
            return None
        return self._mode_map.get(str(raw), str(raw))


class AlexaApplianceConnectivitySensor(AlexaApplianceEntity, SensorEntity):
    """Connectivity status sensor."""

    def __init__(
        self,
        coordinator: AlexaAppliancesCoordinator,
        appliance: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, appliance, "Alexa.EndpointHealth")
        self._attr_name = "Connectivity"

    @property
    def native_value(self) -> str | None:
        val = self._capability_value
        if isinstance(val, dict):
            return val.get("value")
        return str(val) if val is not None else None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlexaAppliancesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []

    for appliance in coordinator.appliances.values():
        for cap in appliance.get("capabilities", []):
            iface = cap.get("interfaceName")
            props = cap.get("properties", {})
            read_only = props.get("readOnly", False)

            if iface == "Alexa.ModeController" and read_only:
                entities.append(
                    AlexaApplianceSensor(coordinator, appliance, cap)
                )
            elif iface == "Alexa.EndpointHealth":
                entities.append(
                    AlexaApplianceConnectivitySensor(coordinator, appliance)
                )

    async_add_entities(entities)
