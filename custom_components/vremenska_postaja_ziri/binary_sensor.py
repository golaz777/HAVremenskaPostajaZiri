"""Binary sensor platform for Vremenska postaja Žiri."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, STALE_AFTER
from .entity import VremenskaPostajaZiriEntity

STALE_DESCRIPTION = BinarySensorEntityDescription(
    key="stale",
    name="Zastareli podatki",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([VremenskaPostajaZiriStaleSensor(coordinator, STALE_DESCRIPTION)])


class VremenskaPostajaZiriStaleSensor(VremenskaPostajaZiriEntity, BinarySensorEntity):
    """On when the newest row of the 5-minute table is too old.

    Unknown while the table is empty (header fallback), because the header
    carries no measurement time.
    """

    @property
    def is_on(self) -> bool | None:
        """Return True if the table data is stale."""
        measured_at = (self.coordinator.data or {}).get("measured_at")
        if measured_at is None:
            return None
        return dt_util.utcnow() - measured_at > STALE_AFTER

    @property
    def extra_state_attributes(self) -> dict:
        """Return the measurement time the check is based on."""
        data = self.coordinator.data or {}
        return {"measured_at": data.get("measured_at")}
