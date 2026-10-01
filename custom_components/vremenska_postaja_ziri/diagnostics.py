"""Diagnostics for Vremenska postaja Žiri.

Download from Settings → Devices & services → Vremenska postaja Žiri → ⋮ →
Download diagnostics. The integration has no credentials, so nothing is redacted.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return what the integration last fetched and which sources fail."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    return {
        "options": dict(entry.options),
        "last_update_success": coordinator.last_update_success,
        "sources": {
            name: {
                "group": source.group,
                "interval": str(source.interval),
                "last_success": coordinator.fetched_at.get(name),
                "failing_since": (f := coordinator.failures.get(name)) and f.since,
                "error": f.error if f else None,
            }
            for name, source in coordinator.sources.items()
        },
        "data": coordinator.data,
    }
