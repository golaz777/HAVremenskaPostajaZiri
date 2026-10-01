"""HTML parsing for vreme-ziri.si.

Kept free of Home Assistant imports so it can be unit tested on its own.
"""
from __future__ import annotations

from datetime import date, datetime
import json
import re
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

# All times on vreme-ziri.si are local station time.
LJUBLJANA = ZoneInfo("Europe/Ljubljana")


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


# 16-point compass in Slovenian, as used on the site (S=sever, V=vzhod, J=jug, Z=zahod).
COMPASS_POINTS = [
    "S", "SSV", "SV", "VSV", "V", "VJV", "JV", "JJV",
    "J", "JJZ", "JZ", "ZJZ", "Z", "ZSZ", "SZ", "SSZ",
]


def compass(degrees: float | None) -> str | None:
    """Convert a wind direction in degrees to a 16-point compass name."""
    if degrees is None:
        return None
    return COMPASS_POINTS[round(degrees / 22.5) % 16]


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

    data = {
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
    data["wind_direction"] = compass(data["wind_direction_deg"])
    data["measured_at"] = _local_datetime(data["date"], data["time"], "%d.%m.%Y %H:%M")
    return data


def _local_datetime(day: str, time: str, fmt: str) -> datetime | None:
    try:
        return datetime.strptime(f"{day} {time}", fmt).replace(tzinfo=LJUBLJANA)
    except ValueError:
        return None


# --- today.php: today's extremes --------------------------------------------

# Row label on today.php -> data key. Rows with a time column also get a
# "<key>_time" entry ("HH:MM").
TODAY_FIELDS = {
    "Najvišja dnevna temperatura": "today_temp_max",
    "Najnižja dnevna temperatura": "today_temp_min",
    "Najvišja vlažnost": "today_humidity_max",
    "Najnižja vlažnost": "today_humidity_min",
    "Najmočnejši sunek": "today_gust_max",
    "Najvišja hitrost (povprečje 10 min.)": "today_wind_max",
    "Največja intenziteta": "today_rain_rate_max",
    "Največ dežja v eni uri": "today_rain_hour_max",
    "Najvišji zračni tlak": "today_pressure_max",
    "Najnižji zračni tlak": "today_pressure_min",
    "Najvišji UV indeks": "today_uv_max",
    "Trenutno deževno obdobje": "rain_spell_days",
    "Trenutno sušno obdobje": "dry_spell_days",
}
_FIRST_NUMBER = re.compile(_NUMBER)
_TIME = re.compile(r"^\d{1,2}:\d{2}$")


def parse_today(html: str) -> dict:
    """Parse today's extremes from today.php."""
    soup = BeautifulSoup(html, "html.parser")
    data = {}
    # Not every row carries class="td_data", so look at all of them.
    for row in soup.find_all("tr"):
        cols = row.find_all("td")
        if len(cols) < 2:
            continue
        key = TODAY_FIELDS.get(cols[0].get_text(" ", strip=True))
        if key is None:
            continue
        if match := _FIRST_NUMBER.search(cols[1].get_text(" ", strip=True)):
            value = safe_float(match.group(1))
            # Spell lengths are whole days ("5 Dan").
            data[key] = int(value) if key.endswith("_days") and value is not None else value
        if len(cols) > 2:
            time = cols[2].get_text(strip=True)
            if _TIME.match(time):
                data[f"{key}_time"] = time

    if not data:
        raise ParseError("Could not find today's extremes")
    return data


# --- vodostaj.php: river Sora -----------------------------------------------

_WATER_PATTERNS = {
    "river_flow": re.compile(r"Pretok reke Sore Žiri\s*" + _NUMBER + r"\s*m\s*3\s*/\s*s"),
    "river_level": re.compile(r"Vodostaj reke Sore Žiri\s*" + _NUMBER + r"\s*cm"),
    "river_temperature": re.compile(r"Temperatura reke Sore Žiri\s*" + _NUMBER + r"\s*°\s*C"),
}
_WATER_FLOW_CLASS = re.compile(r"m\s*3\s*/\s*s\s*-*\s*(.*?)\s*Vodostaj reke Sore Žiri")
_WATER_UPDATED = re.compile(
    r"Zadnja posodobitev podatkov:\s*(\d{4}-\d{2}-\d{2})\s*ob\s*(\d{1,2}:\d{2})"
)


def parse_water(html: str) -> dict:
    """Parse flow, level and temperature of the river Sora from vodostaj.php."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)

    data = {}
    for key, pattern in _WATER_PATTERNS.items():
        if match := pattern.search(text):
            data[key] = safe_float(match.group(1))
    if not data:
        raise ParseError("Could not find river Sora values")

    if "river_flow" in data:
        match = _WATER_FLOW_CLASS.search(text)
        data["river_flow_class"] = match.group(1) if match and match.group(1) else None
    if match := _WATER_UPDATED.search(text):
        data["river_measured_at"] = _local_datetime(match.group(1), match.group(2), "%Y-%m-%d %H:%M")
    return data


# --- snezna_kamera_ziri.php: snow depth -------------------------------------

_SNOW_SEASON = re.compile(r"Tabela meritev snežne odeje\s*(\d{4})\s*-\s*(\d{4})")
_SNOW_DAY = re.compile(r"^([A-Za-zČčŠšŽž]+)\s+(\d{1,2})$")
_MONTHS = {
    "januar": 1, "februar": 2, "marec": 3, "april": 4, "maj": 5, "junij": 6,
    "julij": 7, "avgust": 8, "september": 9, "oktober": 10, "november": 11,
    "december": 12,
}


def parse_snow(html: str) -> dict:
    """Parse the latest manual snow measurement.

    The table is newest-first. The newest rows are "-" placeholders or live
    Google chart iframes with no text, so the first row with a number in the
    total column is the latest usable measurement.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find(string=_SNOW_SEASON)
    if title is None:
        raise ParseError("Could not find snow measurement table")
    first_year, second_year = (int(y) for y in _SNOW_SEASON.search(title).groups())

    for row in title.find_all_next("tr"):
        cols = row.find_all("td")
        if len(cols) < 4:
            continue
        day = _SNOW_DAY.match(cols[0].get_text(" ", strip=True))
        depth = safe_float(cols[3].get_text(strip=True))
        if day is None or depth is None:
            continue
        month = _MONTHS.get(day.group(1).lower())
        if month is None:
            continue
        # A season runs from autumn of the first year into spring of the second.
        year = first_year if month >= 7 else second_year
        notes = cols[4].get_text(" ", strip=True) if len(cols) > 4 else ""
        return {
            "snow_measured": date(year, month, int(day.group(2))),
            "snow_new": safe_float(cols[2].get_text(strip=True)),
            "snow_depth": depth,
            "snow_notes": notes or None,
        }

    raise ParseError("No snow measurements found")


# --- Google Sheets: PM / AQI ------------------------------------------------


def parse_pm(text: str) -> dict:
    """Parse the latest PM/AQI row from a Google Sheets gviz response.

    Returns an empty dict when the sheet has no rows for today yet.
    """
    # The response is wrapped in a JS callback: /*O_o*/\ngoogle.visualization.Query.setResponse({...});
    if not text.startswith("/*O_o*/"):
        raise ParseError("Unexpected PM data format")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ParseError("Unexpected PM data format")

    rows = json.loads(text[start : end + 1]).get("table", {}).get("rows", [])
    if not rows:
        return {}

    # Get the latest row
    cells = rows[-1].get("c", [])

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
                return safe_float(val)
        return None

    return {
        "valPM1": get_val(2),
        "valPM25": get_val(3),
        "valPM10": get_val(5),
        "valAQI": get_val(7),
        "valAQI1h": get_val(8),
    }
