"""Select entities for Alexa Appliances."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import AlexaAppliancesConfigEntry, AlexaAppliancesCoordinator
from .entity import AlexaApplianceEntity


class AlexaApplianceMode(AlexaApplianceEntity, SelectEntity):
    """A writable mode controller exposed as a select."""

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
        friendly = (
            capability.get("resources", {}).get("friendlyNames", [{}])[0]
            .get("value", {})
            .get("text", f"Mode {instance}")
        )
        self._attr_name = friendly

        self._label_to_value: dict[str, str] = {}
        self._value_to_label: dict[str, str] = {}
        options: list[str] = []
        for mode in capability.get("configuration", {}).get("supportedModes", []):
            names = mode.get("modeResources", {}).get("friendlyNames", [])
            label = names[0]["value"]["text"] if names else mode["value"]
            self._label_to_value[label] = mode["value"]
            self._value_to_label[mode["value"]] = label
            options.append(label)
        self._attr_options = options

    @property
    def current_option(self) -> str | None:
        raw = self._capability_value
        if raw is None:
            return None
        return self._value_to_label.get(str(raw), str(raw))

    async def async_select_option(self, option: str) -> None:
        value = self._label_to_value.get(option, option)
        await self.coordinator.api.set_state(
            self._alexa_entity_id,
            {"action": "setMode", "instance": self._instance, "mode": value},
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlexaAppliancesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = []

    for appliance in coordinator.appliances.values():
        for cap in appliance.get("capabilities", []):
            iface = cap.get("interfaceName")
            props = cap.get("properties", {})
            read_only = props.get("readOnly", False)

            if iface == "Alexa.ModeController" and not read_only:
                entities.append(
                    AlexaApplianceMode(coordinator, appliance, cap)
                )

    async_add_entities(entities)
