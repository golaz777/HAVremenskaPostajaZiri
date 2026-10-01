"""Integration tests: set up the config entry against mocked pages."""
from pathlib import Path

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.vremenska_postaja_ziri.const import (
    DOMAIN,
    GOOGLE_SHEETS_BASE_URL,
    SNOW_URL,
    TODAY_URL,
    URL,
    WATER_URL,
)

FIXTURES = Path(__file__).parent / "fixtures"
PM_URL = GOOGLE_SHEETS_BASE_URL.split("?")[0]
PM_RESPONSE = (
    "/*O_o*/\ngoogle.visualization.Query.setResponse("
    '{"table":{"rows":[{"c":[{"v":"00:10"},null,{"v":4},{"v":6},null,{"v":8},null,{"v":20},{"v":21}]}]}});'
)


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
    ):
        aioclient_mock.get(url, text=body, status=500 if url in failing else 200)


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={})
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


async def test_header_fallback(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    _mock_pages(aioclient_mock, weather_page="tabelaricni_dan_no_rows.html")
    await _setup(hass)

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
    _mock_pages(aioclient_mock, failing=(URL, TODAY_URL, WATER_URL, SNOW_URL, PM_URL))
    entry = MockConfigEntry(domain=DOMAIN, data={})
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
