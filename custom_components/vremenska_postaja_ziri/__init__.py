"""The Vremenska postaja Žiri integration."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import json
import re

import async_timeout
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN, UPDATE_INTERVAL_MINUTES, URL, GOOGLE_SHEETS_BASE_URL
from .scraper import ParseError, parse_weather_html

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

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
    """Class to manage fetching data from Vremenska postaja Žiri."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self._source: str | None = None

    async def _async_update_data(self):
        """Fetch data from URL."""
        data = {}
        try:
            async with async_timeout.timeout(30):
                async with aiohttp.ClientSession() as session:
                    # Fetch weather data
                    async with session.get(URL) as response:
                        if response.status == 200:
                            html = await response.text()
                            data.update(self._parse_html(html))
                        else:
                            _LOGGER.warning("Error fetching weather data: %s", response.status)

                    # Fetch PM data
                    pm_data = await self._fetch_pm_data(session)
                    if pm_data:
                        data.update(pm_data)

        except Exception as err:
            if not data:
                raise UpdateFailed(f"Error communicating with API: {err}")
            _LOGGER.warning("Error updating some data: %s", err)

        if not data:
            raise UpdateFailed("Failed to fetch any data")
        
        return data

    async def _fetch_pm_data(self, session: aiohttp.ClientSession):
        """Fetch PM data from Google Sheets."""
        try:
            now = dt_util.now()
            day_str = now.strftime("%d.%m.%Y")
            sheet_name = f"Air{now.year}-{now.month:02d}"
            
            tq = f"select B,D,E,F,G,H,I,J,K where A='{day_str}'"
            url = f"{GOOGLE_SHEETS_BASE_URL}&tq={aiohttp.helpers.quote(tq)}&sheet={sheet_name}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    _LOGGER.warning("Error fetching PM data: %s", response.status)
                    return None
                
                text = await response.text()
                # The response is wrapped in a JS callback: /*O_o*/\ngoogle.visualization.Query.setResponse({...});
                if not text.startswith("/*O_o*/"):
                    _LOGGER.warning("Unexpected PM data format")
                    return None
                
                # Extract JSON
                start = text.find("{")
                end = text.rfind("}")
                if start == -1 or end == -1:
                    return None
                
                json_str = text[start : end + 1]
                data = json.loads(json_str)
                
                rows = data.get("table", {}).get("rows", [])
                if not rows:
                    return None
                
                # Get the latest row
                latest_row = rows[-1]
                cells = latest_row.get("c", [])
                
                # Mapping based on JS fetchDay:
                # cells[0] -> time (B)
                # cells[2] -> pm1 (E)
                # cells[3] -> pm25 (F)
                # cells[5] -> pm10 (H)
                # cells[7] -> aqi (J)
                # cells[8] -> aqi1h (K)
                
                def get_val(idx):
                    if idx < len(cells) and cells[idx] and "v" in cells[idx]:
                        val = cells[idx]["v"]
                        if isinstance(val, (int, float)):
                            return val
                        if isinstance(val, str):
                            try:
                                return float(val.replace(",", "."))
                            except ValueError:
                                return None
                    return None

                return {
                    "valPM1": get_val(2),
                    "valPM25": get_val(3),
                    "valPM10": get_val(5),
                    "valAQI": get_val(7),
                    "valAQI1h": get_val(8),
                }

        except Exception as err:
            _LOGGER.warning("Failed to fetch PM data: %s", err)
            return None

    def _parse_html(self, html: str):
        """Parse the HTML table, falling back to the page header."""
        try:
            data = parse_weather_html(html)
        except ParseError as err:
            raise UpdateFailed(str(err)) from err

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
