"""Base entity for Vremenska postaja Žiri."""
from __future__ import annotations

from collections.abc import Iterable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VremenskaPostajaZiriCoordinator, enabled_groups
from .const import (
    DOMAIN,
    GROUP_PM,
    GROUP_SNOW,
    GROUP_TODAY,
    GROUP_WATER,
    GROUP_YEAR,
    GROUP_YESTERDAY,
)


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


def group_for_key(key: str) -> str | None:
    """Optional data group an entity belongs to; None = always on."""
    if key.startswith("today_") or key in ("dry_spell_days", "rain_spell_days"):
        return GROUP_TODAY
    if key.startswith("yesterday_"):
        return GROUP_YESTERDAY
    if key.startswith("year_"):
        return GROUP_YEAR
    if key.startswith("river_"):
        return GROUP_WATER
    if key.startswith("snow_"):
        return GROUP_SNOW
    if key.startswith("val"):
        return GROUP_PM
    return None


def enabled_descriptions(
    hass: HomeAssistant,
    entry: ConfigEntry,
    platform: str,
    descriptions: Iterable[EntityDescription],
) -> list[EntityDescription]:
    """Descriptions whose group is enabled; remove entities of disabled groups.

    Removing them (instead of leaving "no longer provided" leftovers) keeps the
    entity list clean; re-enabling the group creates them again.
    """
    groups = enabled_groups(entry)
    registry = er.async_get(hass)
    enabled = []
    for description in descriptions:
        group = group_for_key(description.key)
        if group is None or group in groups:
            enabled.append(description)
        elif entity_id := registry.async_get_entity_id(
            platform, DOMAIN, f"{DOMAIN}_{description.key}"
        ):
            registry.async_remove(entity_id)
    return enabled
