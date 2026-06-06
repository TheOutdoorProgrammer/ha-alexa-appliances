"""Switch entities for Alexa Appliances."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AlexaAppliancesConfigEntry, AlexaAppliancesCoordinator
from .entity import AlexaApplianceEntity


class AlexaApplianceToggle(AlexaApplianceEntity, SwitchEntity):
    """A toggle controller exposed as a switch."""

    def __init__(
        self,
        coordinator: AlexaAppliancesCoordinator,
        appliance: dict[str, Any],
        capability: dict[str, Any],
    ) -> None:
        instance = capability["instance"]
        super().__init__(
            coordinator, appliance, "Alexa.ToggleController", instance
        )
        friendly = (
            capability.get("resources", {}).get("friendlyNames", [{}])[0]
            .get("value", {})
            .get("text", f"Toggle {instance}")
        )
        self._attr_name = friendly

    @property
    def is_on(self) -> bool | None:
        val = self._capability_value
        if val is None:
            return None
        return val == "ON"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_state(
            self._alexa_entity_id,
            {
                "action": "setToggleState",
                "instance": self._instance,
                "toggleState": "ON",
            },
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_state(
            self._alexa_entity_id,
            {
                "action": "setToggleState",
                "instance": self._instance,
                "toggleState": "OFF",
            },
        )
        await self.coordinator.async_request_refresh()


class AlexaAppliancePower(AlexaApplianceEntity, SwitchEntity):
    """Power controller exposed as a switch."""

    def __init__(
        self,
        coordinator: AlexaAppliancesCoordinator,
        appliance: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, appliance, "Alexa.PowerController")
        self._attr_name = "Power"

    @property
    def is_on(self) -> bool | None:
        val = self._capability_value
        if val is None:
            return None
        return val == "ON"

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_state(
            self._alexa_entity_id, {"action": "turnOn"}
        )
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_state(
            self._alexa_entity_id, {"action": "turnOff"}
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlexaAppliancesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SwitchEntity] = []

    for appliance in coordinator.appliances.values():
        for cap in appliance.get("capabilities", []):
            iface = cap.get("interfaceName")
            props = cap.get("properties", {})
            read_only = props.get("readOnly", False)

            if iface == "Alexa.ToggleController" and not read_only:
                entities.append(
                    AlexaApplianceToggle(coordinator, appliance, cap)
                )
            elif iface == "Alexa.PowerController" and not read_only:
                entities.append(
                    AlexaAppliancePower(coordinator, appliance)
                )

    async_add_entities(entities)
