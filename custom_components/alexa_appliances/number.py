"""Number entities for Alexa Appliances."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AlexaAppliancesConfigEntry, AlexaAppliancesCoordinator
from .entity import AlexaApplianceEntity


class AlexaApplianceRange(AlexaApplianceEntity, NumberEntity):
    """A range controller exposed as a number."""

    def __init__(
        self,
        coordinator: AlexaAppliancesCoordinator,
        appliance: dict[str, Any],
        capability: dict[str, Any],
    ) -> None:
        instance = capability["instance"]
        super().__init__(
            coordinator, appliance, "Alexa.RangeController", instance
        )
        friendly = (
            capability.get("resources", {}).get("friendlyNames", [{}])[0]
            .get("value", {})
            .get("text", f"Range {instance}")
        )
        self._attr_name = friendly

        supported = capability.get("configuration", {}).get("supportedRange", {})
        self._attr_native_min_value = supported.get("minimumValue", 0)
        self._attr_native_max_value = supported.get("maximumValue", 100)
        self._attr_native_step = supported.get("precision", 1)

    @property
    def native_value(self) -> float | None:
        val = self._capability_value
        if val is None:
            return None
        return float(val)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.api.set_state(
            self._alexa_entity_id,
            {
                "action": "setRangeValue",
                "instance": self._instance,
                "rangeValue": value,
            },
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlexaAppliancesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[NumberEntity] = []

    for appliance in coordinator.appliances.values():
        for cap in appliance.get("capabilities", []):
            iface = cap.get("interfaceName")
            props = cap.get("properties", {})
            read_only = props.get("readOnly", False)

            if iface == "Alexa.RangeController" and not read_only:
                entities.append(
                    AlexaApplianceRange(coordinator, appliance, cap)
                )

    async_add_entities(entities)
