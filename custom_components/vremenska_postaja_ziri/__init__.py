"""The Vremenska postaja Žiri integration."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
import logging
from urllib.parse import quote

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    CONF_GROUPS,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GOOGLE_SHEETS_BASE_URL,
    GROUP_PM,
    GROUP_SNOW,
    GROUP_TODAY,
    GROUP_WATER,
    GROUP_YEAR,
    GROUP_YESTERDAY,
    GROUPS,
    REPAIR_AFTER,
    REQUEST_TIMEOUT_SECONDS,
    RIVER_TREND_INTERVAL,
    SNOW_INTERVAL,
    SNOW_URL,
    TODAY_INTERVAL,
    TODAY_URL,
    URL,
    WATER_INTERVAL,
    WATER_URL,
    YEAR_INTERVAL,
    YEAR_URL,
    YESTERDAY_INTERVAL,
    YESTERDAY_URL,
)
from .scraper import (
    RIVER_SHEET_URL,
    parse_pm,
    parse_river_trend,
    parse_snow,
    parse_today,
    parse_water,
    parse_weather_html,
    parse_year,
    parse_yesterday,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]

SOURCE_NAMES = ["weather", "pm", "today", "yesterday", "year", "water", "river_trend", "snow"]


def enabled_groups(entry: ConfigEntry) -> list[str]:
    """Optional data groups enabled for this entry (all by default)."""
    return list(entry.options.get(CONF_GROUPS, GROUPS))


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Vremenska postaja Žiri component."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Vremenska postaja Žiri from a config entry."""
    coordinator = VremenskaPostajaZiriCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))

    return True

async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload so changed groups and intervals take effect."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove any Repairs issues left behind."""
    for name in SOURCE_NAMES:
        ir.async_delete_issue(hass, DOMAIN, issue_id(name))


def issue_id(source: str) -> str:
    """Repairs issue id for a failing source."""
    return f"source_failing_{source}"


@dataclass
class Source:
    """One page or sheet the coordinator reads."""

    group: str | None  # None = always on
    interval: timedelta
    fetch: Callable[[aiohttp.ClientSession], Awaitable[dict]]


@dataclass
class Failure:
    """A source that is currently failing."""

    since: datetime
    error: str


class VremenskaPostajaZiriCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from Vremenska postaja Žiri.

    Each page (source) is fetched on its own interval and fails on its own:
    a broken PM sheet no longer takes the weather sensors down with it, and
    vice versa. The update only fails when no source has any data. A source
    failing for longer than REPAIR_AFTER raises a Repairs issue.
    """

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        scan_interval = timedelta(
            minutes=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=scan_interval,
        )
        self.entry = entry
        self.groups = enabled_groups(entry)
        self._source: str | None = None

        page = self._fetch_page
        all_sources = {
            "weather": Source(None, scan_interval, self._fetch_weather),
            "pm": Source(GROUP_PM, scan_interval, self._fetch_pm_data),
            "today": Source(GROUP_TODAY, TODAY_INTERVAL, partial(page, url=TODAY_URL, parser=parse_today)),
            "yesterday": Source(
                GROUP_YESTERDAY, YESTERDAY_INTERVAL, partial(page, url=YESTERDAY_URL, parser=parse_yesterday)
            ),
            "year": Source(GROUP_YEAR, YEAR_INTERVAL, partial(page, url=YEAR_URL, parser=parse_year)),
            "water": Source(GROUP_WATER, WATER_INTERVAL, partial(page, url=WATER_URL, parser=parse_water)),
            "river_trend": Source(GROUP_WATER, RIVER_TREND_INTERVAL, self._fetch_river_trend),
            "snow": Source(GROUP_SNOW, SNOW_INTERVAL, partial(page, url=SNOW_URL, parser=parse_snow)),
        }
        self.sources = {
            name: source
            for name, source in all_sources.items()
            if source.group is None or source.group in self.groups
        }
        self.fetched_at: dict[str, datetime] = {}
        self.failures: dict[str, Failure] = {}
        self._results: dict[str, dict] = {}

        # Issues for sources that are now switched off can never clear themselves.
        for name in SOURCE_NAMES:
            if name not in self.sources:
                ir.async_delete_issue(hass, DOMAIN, issue_id(name))

    async def _async_update_data(self):
        """Fetch every source that is due and merge the results."""
        session = async_get_clientsession(self.hass)
        now = dt_util.utcnow()

        for name, source in self.sources.items():
            last = self.fetched_at.get(name)
            if last is not None and now - last < source.interval:
                continue
            try:
                self._results[name] = await source.fetch(session)
            except Exception as err:  # noqa: BLE001 - each source fails on its own
                self._results[name] = {}
                self.fetched_at.pop(name, None)  # retry on the next poll
                self._source_failed(name, err, now)
                continue
            self.fetched_at[name] = now
            self._source_recovered(name)

        data = {}
        for result in self._results.values():
            data.update(result)

        if not data:
            errors = "; ".join(f"{name}: {f.error}" for name, f in self.failures.items())
            raise UpdateFailed(f"Failed to fetch any data ({errors})")

        return data

    def _source_failed(self, name: str, err: Exception, now: datetime) -> None:
        failure = self.failures.get(name)
        if failure is None:
            _LOGGER.warning("Error updating %s data: %s", name, err)
            failure = self.failures[name] = Failure(since=now, error=str(err))
        else:
            _LOGGER.debug("Error updating %s data: %s", name, err)
            failure.error = str(err)

        if now - failure.since >= REPAIR_AFTER:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id(name),
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="source_failing",
                translation_placeholders={
                    "source": name,
                    "since": dt_util.as_local(failure.since).strftime("%Y-%m-%d %H:%M"),
                    "error": failure.error,
                },
            )

    def _source_recovered(self, name: str) -> None:
        if self.failures.pop(name, None) is not None:
            _LOGGER.info("Updating %s data works again", name)
            ir.async_delete_issue(self.hass, DOMAIN, issue_id(name))

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
        data = await self._fetch_page(
            session, URL, partial(parse_weather_html, now=dt_util.now())
        )

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

    async def _fetch_river_trend(self, session: aiohttp.ClientSession) -> dict:
        """Fetch the river Sora trend from the Google Sheet behind vodostaj.php."""
        return parse_river_trend(await self._fetch_text(session, RIVER_SHEET_URL))

    async def _fetch_pm_data(self, session: aiohttp.ClientSession) -> dict:
        """Fetch PM data from Google Sheets."""
        now = dt_util.now()
        day_str = now.strftime("%d.%m.%Y")
        sheet_name = f"Air{now.year}-{now.month:02d}"

        tq = f"select B,D,E,F,G,H,I,J,K where A='{day_str}'"
        url = f"{GOOGLE_SHEETS_BASE_URL}&tq={quote(tq)}&sheet={sheet_name}"

        return parse_pm(await self._fetch_text(session, url))
