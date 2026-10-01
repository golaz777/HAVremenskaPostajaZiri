"""HTML parsing for vreme-ziri.si.

Kept free of Home Assistant imports so it can be unit tested on its own.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup


class ParseError(Exception):
    """Raised when no weather data can be extracted from the page."""


# The page header shows the current values, e.g.
# "Trenutno na meteorološki postaji ŽIRI: 20,9 °C | 50 % | 12,9 km/h | 0,0 mm".
# It stays populated when the 5-minute table is empty (e.g. at the start of a
# month), so it is used as a fallback for these four values.
_NUMBER = r"([-−]?\d+(?:[.,]\d+)?)"
_HEADER_PATTERNS = {
    "temperature": re.compile(_NUMBER + r"\s*°\s*C"),
    "humidity": re.compile(_NUMBER + r"\s*%"),
    "wind_speed": re.compile(_NUMBER + r"\s*km/h"),
    "rain_total": re.compile(_NUMBER + r"\s*mm\b"),
}
_HEADER_MARKER = "Trenutno na"


def safe_float(val):
    """Convert a Slovenian-formatted number ("12,4") to float, or None."""
    try:
        return float(val.replace(",", ".").replace("−", "-"))
    except (ValueError, TypeError, AttributeError):
        return None


def parse_weather_html(html: str) -> dict:
    """Parse the latest measurements, falling back to the header values.

    The result carries a ``source`` key: ``"table"`` or ``"header"``.
    """
    soup = BeautifulSoup(html, "html.parser")
    try:
        data = _parse_table(soup)
        data["source"] = "table"
        return data
    except ParseError as table_err:
        try:
            data = _parse_header_soup(soup)
        except ParseError as header_err:
            raise ParseError(f"{table_err}; {header_err}") from header_err
        data["source"] = "header"
        data["table_error"] = str(table_err)
        return data


def parse_header(html: str) -> dict:
    """Parse temperature, humidity, wind speed and rainfall from the header."""
    return _parse_header_soup(BeautifulSoup(html, "html.parser"))


def _parse_header_soup(soup: BeautifulSoup) -> dict:
    ident = soup.find(id="ident")
    if ident is not None:
        text = ident.get_text(" ", strip=True)
    else:
        text = soup.get_text(" ", strip=True)
        start = text.find(_HEADER_MARKER)
        if start == -1:
            raise ParseError("Could not find current values in page header")
        # Only the short header line, not the table column titles further down.
        text = text[start : start + 200]

    data = {}
    for key, pattern in _HEADER_PATTERNS.items():
        if match := pattern.search(text):
            value = safe_float(match.group(1))
            if value is not None:
                data[key] = value

    if not data:
        raise ParseError("Could not find current values in page header")
    return data


def _parse_table(soup: BeautifulSoup) -> dict:
    # The data table is the one with cellspacing="0" and cellpadding="3"
    tables = soup.find_all("table", {"cellpadding": "3", "cellspacing": "0"})
    if not tables:
        raise ParseError("Could not find data table in HTML")

    data_table = tables[0]
    rows = data_table.find_all("tr")

    # Header is at rows[0]
    # Data rows have class vrstica0 or vrstica1
    data_rows = [row for row in rows if row.get("class") in (["vrstica0"], ["vrstica1"])]

    if not data_rows:
        raise ParseError("No data rows found in table")

    # The latest data is at the end of the table (it's chronological)
    latest_row = data_rows[-1]
    cols = latest_row.find_all("td")

    if len(cols) < 15:
        raise ParseError(f"Unexpected number of columns: {len(cols)}")

    # Column mapping based on observation:
    # 0: Datum
    # 1: Čas meritve
    # 2: Temperatura (°C)
    # 3: Vlažnost (%)
    # 4: Hitrost vetra (km/h)
    # 5: Sunek vetra (km/h)
    # 6: smer vetra (°)
    # 7: Jakost padavin (mm/h)
    # 8: Vsota padavin (mm)
    # 9: Zračni tlak (mb)
    # 10: UV indeks
    # 11: Sončno obsevanje (w/m2)
    # 12: ET izhlapevanje (mm)
    # 13: Prev. smer vetra
    # 14: trajanje sončnega obsevanja (h)

    return {
        "date": cols[0].get_text(strip=True),
        "time": cols[1].get_text(strip=True),
        "temperature": safe_float(cols[2].get_text(strip=True)),
        "humidity": safe_float(cols[3].get_text(strip=True)),
        "wind_speed": safe_float(cols[4].get_text(strip=True)),
        "wind_gust": safe_float(cols[5].get_text(strip=True)),
        "wind_direction_deg": safe_float(cols[6].get_text(strip=True)),
        "rain_rate": safe_float(cols[7].get_text(strip=True)),
        "rain_total": safe_float(cols[8].get_text(strip=True)),
        "pressure": safe_float(cols[9].get_text(strip=True)),
        "uv_index": safe_float(cols[10].get_text(strip=True)),
        "solar_radiation": safe_float(cols[11].get_text(strip=True)),
        "et_evaporation": safe_float(cols[12].get_text(strip=True)),
        "prevailing_wind_direction": cols[13].get_text(strip=True),
        "sunshine_duration": safe_float(cols[14].get_text(strip=True)),
    }
