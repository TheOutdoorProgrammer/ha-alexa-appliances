"""Base entity for Alexa Appliances."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AlexaAppliancesCoordinator


class AlexaApplianceEntity(CoordinatorEntity[AlexaAppliancesCoordinator]):
    """Base class for Alexa Appliance entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlexaAppliancesCoordinator,
        appliance: dict[str, Any],
        capability_name: str,
        instance: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._appliance = appliance
        self._alexa_entity_id = appliance["entityId"]
        self._namespace = capability_name
        self._instance = instance

        appliance_id = appliance["applianceId"]
        suffix = f"_{instance}" if instance else ""
        self._attr_unique_id = f"{appliance_id}_{capability_name}{suffix}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, appliance_id)},
            name=appliance["friendlyName"],
            manufacturer=appliance.get("manufacturerName"),
            model=appliance.get("friendlyDescription") or appliance.get("modelName"),
        )

    @property
    def _capability_value(self) -> Any | None:
        return self.coordinator.get_capability_value(
            self._alexa_entity_id, self._namespace, self._instance
        )
