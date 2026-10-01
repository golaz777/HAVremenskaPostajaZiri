"""Base entity for Vremenska postaja Žiri."""
from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VremenskaPostajaZiriCoordinator
from .const import DOMAIN


class VremenskaPostajaZiriEntity(CoordinatorEntity[VremenskaPostajaZiriCoordinator]):
    """An entity on the single Vremenska postaja Žiri device."""

    def __init__(
        self,
        coordinator: VremenskaPostajaZiriCoordinator,
        description: EntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "vremenska_postaja_ziri")},
            name="Vremenska postaja Žiri",
            manufacturer="Vreme Žiri",
            configuration_url="https://www.vreme-ziri.si/tabelaricni_dan.php",
        )
