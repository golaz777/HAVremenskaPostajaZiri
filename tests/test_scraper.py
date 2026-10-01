"""Tests for the HTML scraper (no Home Assistant required)."""
from pathlib import Path

import pytest

from scraper import ParseError, parse_header, parse_weather_html

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
