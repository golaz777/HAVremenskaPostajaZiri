"""The Vremenska postaja Žiri integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
import logging
from urllib.parse import quote

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    GOOGLE_SHEETS_BASE_URL,
    PM_INTERVAL,
    REQUEST_TIMEOUT_SECONDS,
    SNOW_INTERVAL,
    SNOW_URL,
    TODAY_INTERVAL,
    TODAY_URL,
    URL,
    WATER_INTERVAL,
    WATER_URL,
    WEATHER_INTERVAL,
)
from .scraper import (
    parse_pm,
    parse_snow,
    parse_today,
    parse_water,
    parse_weather_html,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Vremenska postaja Žiri component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vremenska postaja Žiri from a config entry."""
    coordinator = VremenskaPostajaZiriCoordinator(hass)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

class VremenskaPostajaZiriCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Vremenska postaja Žiri.

    Each page (source) is fetched on its own interval and fails on its own:
    a broken PM sheet no longer takes the weather sensors down with it, and
    vice versa. The update only fails when no source has any data.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=WEATHER_INTERVAL,
        )
        self._source: str | None = None
        self._sources: dict[str, tuple] = {
            "weather": (WEATHER_INTERVAL, self._fetch_weather),
            "pm": (PM_INTERVAL, self._fetch_pm_data),
            "today": (TODAY_INTERVAL, lambda s: self._fetch_page(s, TODAY_URL, parse_today)),
            "water": (WATER_INTERVAL, lambda s: self._fetch_page(s, WATER_URL, parse_water)),
            "snow": (SNOW_INTERVAL, lambda s: self._fetch_page(s, SNOW_URL, parse_snow)),
        }
        self._results: dict[str, dict] = {}
        self._fetched_at: dict[str, datetime] = {}
        self._failing: set[str] = set()

    async def _async_update_data(self):
        """Fetch every source that is due and merge the results."""
        session = async_get_clientsession(self.hass)
        now = dt_util.utcnow()
        errors = []

        for name, (interval, fetch) in self._sources.items():
            last = self._fetched_at.get(name)
            if last is not None and now - last < interval:
                continue
            try:
                self._results[name] = await fetch(session)
            except Exception as err:  # noqa: BLE001 - each source fails on its own
                errors.append(f"{name}: {err}")
                self._results[name] = {}
                self._fetched_at.pop(name, None)  # retry on the next poll
                if name not in self._failing:
                    _LOGGER.warning("Error updating %s data: %s", name, err)
                    self._failing.add(name)
                else:
                    _LOGGER.debug("Error updating %s data: %s", name, err)
                continue
            self._fetched_at[name] = now
            if name in self._failing:
                _LOGGER.info("Updating %s data works again", name)
                self._failing.discard(name)

        data = {}
        for result in self._results.values():
            data.update(result)

        if not data:
            raise UpdateFailed(f"Failed to fetch any data ({'; '.join(errors)})")

        return data

    async def _fetch_text(self, session: aiohttp.ClientSession, url: str) -> str:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        ) as response:
            response.raise_for_status()
            return await response.text()

    async def _fetch_page(
        self,
        session: aiohttp.ClientSession,
        url: str,
        parser: Callable[[str], dict],
    ) -> dict:
        html = await self._fetch_text(session, url)
        # BeautifulSoup is CPU bound; keep it off the event loop.
        return await self.hass.async_add_executor_job(parser, html)

    async def _fetch_weather(self, session: aiohttp.ClientSession) -> dict:
        """Fetch the 5-minute table, falling back to the page header."""
        data = await self._fetch_page(session, URL, parse_weather_html)

        if data["source"] != self._source:
            if data["source"] == "header":
                _LOGGER.info(
                    "Table data unavailable (%s); using temperature, humidity, "
                    "wind speed and rainfall from the page header",
                    data["table_error"],
                )
            elif self._source == "header":
                _LOGGER.info("Table data available again")
            self._source = data["source"]

        return data

    async def _fetch_pm_data(self, session: aiohttp.ClientSession) -> dict:
        """Fetch PM data from Google Sheets."""
        now = dt_util.now()
        day_str = now.strftime("%d.%m.%Y")
        sheet_name = f"Air{now.year}-{now.month:02d}"

        tq = f"select B,D,E,F,G,H,I,J,K where A='{day_str}'"
        url = f"{GOOGLE_SHEETS_BASE_URL}&tq={quote(tq)}&sheet={sheet_name}"

        return parse_pm(await self._fetch_text(session, url))
