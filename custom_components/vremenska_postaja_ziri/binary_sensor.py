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

from .const import (
    CONF_RIVER_WARNING_LEVEL,
    DEFAULT_RIVER_WARNING_LEVEL,
    DOMAIN,
    STALE_AFTER,
)
from .entity import VremenskaPostajaZiriEntity, enabled_descriptions

STALE_DESCRIPTION = BinarySensorEntityDescription(
    key="stale",
    name="Zastareli podatki",
    device_class=BinarySensorDeviceClass.PROBLEM,
    entity_category=EntityCategory.DIAGNOSTIC,
)

RIVER_WARNING_DESCRIPTION = BinarySensorEntityDescription(
    key="river_high_level",
    name="Visok vodostaj Sore",
    device_class=BinarySensorDeviceClass.SAFETY,
    icon="mdi:home-flood",
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    classes = {
        STALE_DESCRIPTION.key: VremenskaPostajaZiriStaleSensor,
        RIVER_WARNING_DESCRIPTION.key: VremenskaPostajaZiriRiverWarningSensor,
    }
    async_add_entities(
        classes[description.key](coordinator, description)
        for description in enabled_descriptions(
            hass, entry, "binary_sensor", [STALE_DESCRIPTION, RIVER_WARNING_DESCRIPTION]
        )
    )


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


class VremenskaPostajaZiriRiverWarningSensor(VremenskaPostajaZiriEntity, BinarySensorEntity):
    """On (unsafe) when the river Sora is at or above the configured level."""

    @property
    def _threshold(self) -> int:
        return self.coordinator.entry.options.get(
            CONF_RIVER_WARNING_LEVEL, DEFAULT_RIVER_WARNING_LEVEL
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if the river level is at or above the warning level."""
        level = (self.coordinator.data or {}).get("river_level")
        if level is None:
            return None
        return level >= self._threshold

    @property
    def extra_state_attributes(self) -> dict:
        """Return the level, the threshold and the site's own warning lines."""
        data = self.coordinator.data or {}
        return {
            "level": data.get("river_level"),
            "threshold": self._threshold,
            "trend": data.get("river_level_trend"),
            "site_warning_levels": data.get("river_level_warning_levels"),
            "measured_at": data.get("river_measured_at"),
        }
