"""Constants for the Vremenska postaja Žiri integration."""
from datetime import timedelta

DOMAIN = "vremenska_postaja_ziri"
UPDATE_INTERVAL_MINUTES = 5
URL = "https://www.vreme-ziri.si/tabelaricni_dan.php"
TODAY_URL = "https://www.vreme-ziri.si/today.php"
WATER_URL = "https://www.vreme-ziri.si/vodostaj.php"
SNOW_URL = "https://www.vreme-ziri.si/snezna_kamera_ziri.php"
YESTERDAY_URL = "https://www.vreme-ziri.si/yesterday.php"
YEAR_URL = "https://www.vreme-ziri.si/thisyear.php"
PM_URL = "https://www.vreme-ziri.si/prasni-32.html"
SHEET_ID = "1c7xcEzL0_EcOZtXACsSlKf30bL1ly4uh3wRr6WnC9Cw"
GOOGLE_SHEETS_BASE_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:json"

# How often each page is fetched. Pages that change slowly are fetched less
# often to keep the load on this small, privately run site low.
WEATHER_INTERVAL = timedelta(minutes=UPDATE_INTERVAL_MINUTES)
PM_INTERVAL = timedelta(minutes=UPDATE_INTERVAL_MINUTES)
TODAY_INTERVAL = timedelta(minutes=15)
WATER_INTERVAL = timedelta(minutes=15)
SNOW_INTERVAL = timedelta(hours=1)
RIVER_TREND_INTERVAL = timedelta(minutes=15)
YESTERDAY_INTERVAL = timedelta(hours=1)
YEAR_INTERVAL = timedelta(hours=1)
REQUEST_TIMEOUT_SECONDS = 30

# The 5-minute table counts as stale when its newest row is older than this.
STALE_AFTER = timedelta(minutes=30)
# Snow is measured by hand once a day at 7:00; older measurements (e.g. last
# season's, all summer) are reported as unknown rather than as current.
SNOW_MAX_AGE = timedelta(days=3)

# A source failing for longer than this raises a Repairs issue.
REPAIR_AFTER = timedelta(hours=3)

# Options
CONF_GROUPS = "groups"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_RIVER_WARNING_LEVEL = "river_warning_level"

# Optional data groups. The 5-minute weather table is always fetched.
GROUP_TODAY = "today"
GROUP_YESTERDAY = "yesterday"
GROUP_YEAR = "year"
GROUP_WATER = "water"
GROUP_SNOW = "snow"
GROUP_PM = "pm"
GROUPS = [GROUP_TODAY, GROUP_YESTERDAY, GROUP_YEAR, GROUP_WATER, GROUP_SNOW, GROUP_PM]

DEFAULT_SCAN_INTERVAL = UPDATE_INTERVAL_MINUTES  # minutes
MIN_SCAN_INTERVAL = 5
MAX_SCAN_INTERVAL = 60
# Lowest of the warning lines drawn on vreme-ziri.si's river chart (200/240/280 cm).
DEFAULT_RIVER_WARNING_LEVEL = 200  # cm
