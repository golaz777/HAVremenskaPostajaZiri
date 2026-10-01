"""Tests for the HTML scraper (no Home Assistant required)."""
from datetime import date, datetime
from pathlib import Path

import pytest

from scraper import (
    LJUBLJANA,
    ParseError,
    compass,
    parse_header,
    parse_pm,
    parse_snow,
    parse_today,
    parse_water,
    parse_weather_html,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_table_rows_use_latest_row():
    data = parse_weather_html(_load("tabelaricni_dan_with_rows.html"))

    assert data["source"] == "table"
    assert data["date"] == "01.10.2026"
    assert data["time"] == "00:05"
    assert data["temperature"] == 12.1
    assert data["humidity"] == 89
    assert data["wind_speed"] == 1.6
    assert data["wind_gust"] == 4.8
    assert data["rain_rate"] == 1.2
    assert data["rain_total"] == 0.4
    assert data["pressure"] == 1018.0
    assert data["prevailing_wind_direction"] == "J"


def test_no_data_rows_falls_back_to_header():
    """Real page captured while the table was empty ("No data rows found in table")."""
    data = parse_weather_html(_load("tabelaricni_dan_no_rows.html"))

    assert data["source"] == "header"
    assert data["temperature"] == 20.9
    assert data["humidity"] == 50
    assert data["wind_speed"] == 12.9
    assert data["rain_total"] == 0.0
    # Values the header does not carry are absent, not guessed.
    assert "pressure" not in data
    assert "wind_gust" not in data


def test_missing_table_falls_back_to_header():
    html = _load("tabelaricni_dan_with_rows.html").replace('cellpadding="3"', "")

    data = parse_weather_html(html)

    assert data["source"] == "header"
    assert data["temperature"] == 20.9


def test_too_few_columns_falls_back_to_header():
    html = _load("tabelaricni_dan_no_rows.html").replace(
        '<tr><td height="25"> </td></tr>',
        '<tr class="vrstica0"><td>01.10.2026</td><td>00:00</td></tr>',
    )

    data = parse_weather_html(html)

    assert data["source"] == "header"


def test_header_negative_temperature():
    html = (
        '<div id="ident"><p>Trenutno na meteorološki postaji ŽIRI: '
        "<strong>-3,4</strong> °C | <strong> 97</strong> % | "
        "<strong> 0,0</strong> km/h | <strong>12,6</strong> mm</p></div>"
    )

    assert parse_header(html) == {
        "temperature": -3.4,
        "humidity": 97.0,
        "wind_speed": 0.0,
        "rain_total": 12.6,
    }


def test_header_unicode_minus():
    html = '<div id="ident"><strong>−5,0</strong> °C | <strong>80</strong> %</div>'

    data = parse_header(html)

    assert data["temperature"] == -5.0
    assert data["humidity"] == 80.0


def test_no_table_and_no_header_raises_with_both_reasons():
    with pytest.raises(ParseError) as exc:
        parse_weather_html("<html><body>maintenance</body></html>")

    message = str(exc.value)
    assert "Could not find data table in HTML" in message
    assert "header" in message


# --- Table extras -----------------------------------------------------------


def test_table_measured_at_is_local_time():
    data = parse_weather_html(_load("tabelaricni_dan_with_rows.html"))

    assert data["measured_at"] == datetime(2026, 10, 1, 0, 5, tzinfo=LJUBLJANA)


def test_table_wind_direction_compass():
    data = parse_weather_html(_load("tabelaricni_dan_with_rows.html"))

    assert data["wind_direction"] == "JJZ"  # 210°


def test_header_fallback_has_no_measured_at():
    data = parse_weather_html(_load("tabelaricni_dan_no_rows.html"))

    assert "measured_at" not in data
    assert "wind_direction" not in data


@pytest.mark.parametrize(
    ("degrees", "expected"),
    [(0, "S"), (11, "S"), (12, "SSV"), (90, "V"), (180, "J"), (270, "Z"), (348, "SSZ"), (360, "S"), (None, None)],
)
def test_compass(degrees, expected):
    assert compass(degrees) == expected


# --- Today's extremes -------------------------------------------------------


def test_today_extremes():
    data = parse_today(_load("today.html"))

    assert data["today_temp_max"] == 21.0
    assert data["today_temp_max_time"] == "13:10"
    assert data["today_temp_min"] == 6.1
    assert data["today_temp_min_time"] == "07:31"
    assert data["today_humidity_max"] == 95
    assert data["today_humidity_min"] == 47
    assert data["today_gust_max"] == 14.5
    assert data["today_gust_max_time"] == "12:36"
    assert data["today_wind_max"] == 5.3
    assert data["today_rain_rate_max"] == 0.0
    assert data["today_rain_hour_max"] == 0.0
    assert data["today_pressure_max"] == 1028.01
    assert data["today_pressure_min"] == 1026.99
    assert data["today_uv_max"] == 3.6
    # Row is not tagged class="td_data" on the real page.
    assert data["dry_spell_days"] == 5
    assert isinstance(data["dry_spell_days"], int)
    assert data["rain_spell_days"] == 0
    assert "dry_spell_days_time" not in data


def test_today_without_table_raises():
    with pytest.raises(ParseError):
        parse_today("<html><body>nothing</body></html>")


# --- River Sora -------------------------------------------------------------


def test_water():
    data = parse_water(_load("vodostaj.html"))

    assert data == {
        "river_flow": 0.119,
        "river_flow_class": "mali pretok",
        "river_level": 70.0,
        "river_temperature": 12.8,
        "river_measured_at": datetime(2026, 10, 1, 11, 30, tzinfo=LJUBLJANA),
    }


def test_water_without_values_raises():
    with pytest.raises(ParseError):
        parse_water("<html><body>nothing</body></html>")


# --- Snow -------------------------------------------------------------------


def test_snow_uses_latest_numeric_row():
    # Newest rows are "-" placeholders or live Google chart iframes; the
    # latest row with numbers is 4 February 2026 (season 2025-2026).
    data = parse_snow(_load("snezna_kamera_ziri.html"))

    assert data["snow_measured"] == date(2026, 2, 4)
    assert data["snow_depth"] == 0
    assert data["snow_new"] == 0


def test_snow_year_from_season_for_autumn_months():
    html = (
        "<table><tr><th>Tabela meritev snežne odeje 2025-2026</th></tr></table>"
        "<table><tr><td>December 25</td><td>7:00</td><td>2</td><td>3</td><td>Sneži</td></tr></table>"
    )

    data = parse_snow(html)

    assert data == {
        "snow_measured": date(2025, 12, 25),
        "snow_new": 2.0,
        "snow_depth": 3.0,
        "snow_notes": "Sneži",
    }


def test_snow_without_table_raises():
    with pytest.raises(ParseError):
        parse_snow("<html><body>nothing</body></html>")


# --- PM / AQI ---------------------------------------------------------------

_GVIZ = (
    "/*O_o*/\ngoogle.visualization.Query.setResponse("
    '{"version":"0.6","status":"ok","table":{"rows":[%s]}});'
)


def test_pm_latest_row():
    rows = (
        '{"c":[{"v":"00:00"},null,{"v":1},{"v":2},null,{"v":3},null,{"v":10},{"v":11}]},'
        '{"c":[{"v":"00:10"},null,{"v":4.5},{"v":"6,5"},null,{"v":8},null,{"v":20},null]}'
    )

    assert parse_pm(_GVIZ % rows) == {
        "valPM1": 4.5,
        "valPM25": 6.5,
        "valPM10": 8,
        "valAQI": 20,
        "valAQI1h": None,
    }


def test_pm_no_rows_yet_is_empty_not_error():
    assert parse_pm(_GVIZ % "") == {}


def test_pm_bad_format_raises():
    with pytest.raises(ParseError):
        parse_pm("<html>error</html>")
