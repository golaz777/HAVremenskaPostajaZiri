"""Integration tests: set up the config entry against mocked pages."""
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

from custom_components.vremenska_postaja_ziri.const import (
    DOMAIN,
    GOOGLE_SHEETS_BASE_URL,
    SNOW_URL,
    TODAY_URL,
    URL,
    WATER_URL,
    YEAR_URL,
    YESTERDAY_URL,
)
from custom_components.vremenska_postaja_ziri.scraper import RIVER_SHEET_URL

FIXTURES = Path(__file__).parent / "fixtures"
PM_URL = GOOGLE_SHEETS_BASE_URL.split("?")[0]
PM_RESPONSE = (
    "/*O_o*/\ngoogle.visualization.Query.setResponse("
    '{"table":{"rows":[{"c":[{"v":"00:10"},null,{"v":4},{"v":6},null,{"v":8},null,{"v":20},{"v":21}]}]}});'
)


RIVER_URL = RIVER_SHEET_URL.split("?")[0]
ALL_URLS = (URL, TODAY_URL, WATER_URL, SNOW_URL, PM_URL, YESTERDAY_URL, YEAR_URL, RIVER_URL)


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _mock_pages(
    aioclient_mock: AiohttpClientMocker,
    weather_page: str = "tabelaricni_dan_with_rows.html",
    failing: tuple[str, ...] = (),
) -> None:
    """Mock every page; URLs listed in `failing` return HTTP 500."""
    for url, body in (
        (URL, _fixture(weather_page)),
        (TODAY_URL, _fixture("today.html")),
        (WATER_URL, _fixture("vodostaj.html")),
        (SNOW_URL, _fixture("snezna_kamera_ziri.html")),
        (PM_URL, PM_RESPONSE),
        (YESTERDAY_URL, _fixture("yesterday.html")),
        (YEAR_URL, _fixture("thisyear.html")),
        (RIVER_URL, _fixture("river_sheet.txt")),
    ):
        aioclient_mock.get(url, text=body, status=500 if url in failing else 200)


async def _setup(hass: HomeAssistant, options: dict | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _state(hass: HomeAssistant, platform: str, key: str):
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{DOMAIN}_{key}")
    assert entity_id, f"no entity for {key}"
    return hass.states.get(entity_id)


@pytest.mark.freeze_time("2026-10-01 00:10:00+02:00")
async def test_all_sources(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    _mock_pages(aioclient_mock)
    await _setup(hass)

    assert _state(hass, "sensor", "temperature").state == "12.1"
    assert _state(hass, "sensor", "source").state == "table"
    assert _state(hass, "sensor", "wind_direction").state == "JJZ"
    assert _state(hass, "binary_sensor", "stale").state == STATE_OFF

    today_max = _state(hass, "sensor", "today_temp_max")
    assert today_max.state == "21.0"
    assert today_max.attributes["time"] == "13:10"
    assert _state(hass, "sensor", "dry_spell_days").state == "5"

    level = _state(hass, "sensor", "river_level")
    assert level.state == "70.0"
    assert _state(hass, "sensor", "river_flow").attributes["description"] == "mali pretok"

    # Last measurement is from February, too old to report as current.
    snow = _state(hass, "sensor", "snow_depth")
    assert snow.state == STATE_UNKNOWN
    assert str(snow.attributes["measured"]) == "2026-02-04"

    assert _state(hass, "sensor", "valPM25").state == "6"

    yesterday = _state(hass, "sensor", "yesterday_temp_max")
    assert yesterday.state == "19.3"
    assert yesterday.attributes["time"] == "14:52"

    year_max = _state(hass, "sensor", "year_temp_max")
    assert year_max.state == "37.4"
    assert str(year_max.attributes["date"]) == "2026-07-31"
    assert _state(hass, "sensor", "year_dry_spell_max").state == "18"

    assert _state(hass, "sensor", "river_level_trend").state == "steady"
    warning = _state(hass, "binary_sensor", "river_high_level")
    assert warning.state == STATE_OFF  # 70 cm < default 200 cm
    assert warning.attributes["threshold"] == 200
    assert warning.attributes["site_warning_levels"] == [200.0, 240.0, 280.0]


@pytest.mark.freeze_time("2026-10-01 01:00:00+02:00")
async def test_old_table_row_is_stale(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    _mock_pages(aioclient_mock)
    await _setup(hass)

    assert _state(hass, "binary_sensor", "stale").state == STATE_ON


@pytest.mark.freeze_time("2026-02-05 08:00:00+01:00")
async def test_recent_snow_measurement_is_reported(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    _mock_pages(aioclient_mock)
    await _setup(hass)

    assert _state(hass, "sensor", "snow_depth").state == "0.0"


@pytest.mark.freeze_time("2026-10-01 13:47:00+02:00")
async def test_header_fallback(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    _mock_pages(aioclient_mock, weather_page="tabelaricni_dan_no_rows.html")
    await _setup(hass)

    assert _state(hass, "sensor", "date").state == "01.10.2026"
    assert _state(hass, "sensor", "time").state == "13:47"

    assert _state(hass, "sensor", "source").state == "header"
    assert _state(hass, "sensor", "temperature").state == "20.9"
    assert _state(hass, "sensor", "pressure").state == STATE_UNKNOWN
    assert _state(hass, "binary_sensor", "stale").state == STATE_UNKNOWN


async def test_pm_failure_does_not_affect_weather(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    _mock_pages(aioclient_mock, failing=(PM_URL,))
    await _setup(hass)

    assert _state(hass, "sensor", "temperature").state == "12.1"
    assert _state(hass, "sensor", "valPM25").state == STATE_UNKNOWN


async def test_weather_failure_does_not_affect_other_sources(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    _mock_pages(aioclient_mock, failing=(URL,))
    await _setup(hass)

    assert _state(hass, "sensor", "temperature").state == STATE_UNKNOWN
    assert _state(hass, "sensor", "river_level").state == "70.0"
    assert _state(hass, "sensor", "valPM25").state == "6"


async def test_all_sources_failing_retries_setup(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    _mock_pages(aioclient_mock, failing=ALL_URLS)
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY



# --- Options ------------------------------------------------------------------


def _requests_to(aioclient_mock: AiohttpClientMocker, url: str) -> int:
    return sum(1 for _, request_url, _, _ in aioclient_mock.mock_calls if str(request_url).startswith(url))


async def test_options_flow_disables_groups(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    _mock_pages(aioclient_mock)
    entry = await _setup(hass)
    assert _state(hass, "sensor", "snow_depth") is not None

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "groups": ["today", "water"],
            "scan_interval": 15.0,
            "river_warning_level": 60.0,
        },
    )
    await hass.async_block_till_done()
    assert entry.options == {
        "groups": ["today", "water"],
        "scan_interval": 15,
        "river_warning_level": 60,
    }

    registry = er.async_get(hass)
    for platform, key in (("sensor", "snow_depth"), ("sensor", "valPM25"), ("sensor", "year_temp_max")):
        assert registry.async_get_entity_id(platform, DOMAIN, f"{DOMAIN}_{key}") is None
    assert _state(hass, "sensor", "today_temp_max").state == "21.0"
    # The lower threshold applies after the reload: 70 cm >= 60 cm.
    assert _state(hass, "binary_sensor", "river_high_level").state == STATE_ON

    coordinator = hass.data[DOMAIN][entry.entry_id]
    assert set(coordinator.sources) == {"weather", "today", "water", "river_trend"}
    assert coordinator.update_interval.total_seconds() == 15 * 60


async def test_disabled_groups_are_not_fetched(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    _mock_pages(aioclient_mock)
    await _setup(hass, options={"groups": []})

    assert _requests_to(aioclient_mock, URL) == 1
    for url in (TODAY_URL, WATER_URL, SNOW_URL, PM_URL, YESTERDAY_URL, YEAR_URL, RIVER_URL):
        assert _requests_to(aioclient_mock, url) == 0, url
    assert _state(hass, "sensor", "temperature").state == "12.1"
    assert er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{DOMAIN}_river_high_level"
    ) is None


# --- Repairs ------------------------------------------------------------------


async def test_long_failure_raises_repair_issue_and_recovery_clears_it(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, freezer
) -> None:
    freezer.move_to("2026-10-01 10:00:00+00:00")
    _mock_pages(aioclient_mock, failing=(SNOW_URL,))
    entry = await _setup(hass)
    coordinator = hass.data[DOMAIN][entry.entry_id]
    issues = ir.async_get(hass)

    freezer.move_to("2026-10-01 12:00:00+00:00")
    await coordinator.async_refresh()
    assert issues.async_get_issue(DOMAIN, "source_failing_snow") is None  # only 2 h

    freezer.move_to("2026-10-01 13:00:00+00:00")
    await coordinator.async_refresh()
    issue = issues.async_get_issue(DOMAIN, "source_failing_snow")
    assert issue is not None
    assert issue.translation_placeholders["source"] == "snow"

    aioclient_mock.clear_requests()
    _mock_pages(aioclient_mock)
    freezer.move_to("2026-10-01 13:05:00+00:00")
    await coordinator.async_refresh()
    assert issues.async_get_issue(DOMAIN, "source_failing_snow") is None


async def test_disabling_a_group_clears_its_issue(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    ir.async_create_issue(
        hass, DOMAIN, "source_failing_snow", is_fixable=False,
        severity=ir.IssueSeverity.WARNING, translation_key="source_failing",
        translation_placeholders={"source": "snow", "since": "-", "error": "-"},
    )
    _mock_pages(aioclient_mock)
    await _setup(hass, options={"groups": ["today"]})

    assert ir.async_get(hass).async_get_issue(DOMAIN, "source_failing_snow") is None


# --- Diagnostics --------------------------------------------------------------


async def test_diagnostics(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, hass_client) -> None:
    _mock_pages(aioclient_mock, failing=(PM_URL,))
    entry = await _setup(hass)

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["sources"]["weather"]["error"] is None
    assert diagnostics["sources"]["weather"]["last_success"] is not None
    assert "500" in diagnostics["sources"]["pm"]["error"]
    assert diagnostics["data"]["temperature"] == 12.1
