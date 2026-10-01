# CLAUDE.md

Guidance for AI assistants working in this repository.

## Project

Home Assistant custom integration (domain `vremenska_postaja_ziri`) that
scrapes https://www.vreme-ziri.si/tabelaricni_dan.php for weather data and a
Google Sheet for PM/AQI data. Distributed through **HACS** as a custom
repository.

## Repository layout

HACS layout: the integration lives in `custom_components/vremenska_postaja_ziri/`,
`hacs.json` is at the repo root. Do not move the integration back to the root —
HACS requires this layout.

- `scraper.py` — all HTML parsing. **No Home Assistant imports** so the tests
  can import it directly (`pythonpath` in `pyproject.toml`). Keep it that way.
- `__init__.py` — `DataUpdateCoordinator`. Polls every `scan_interval` option
  (default 5 min) but fetches each `Source` only when its own interval in
  `const.py` is due. Each source belongs to an optional **group** (`GROUPS`;
  `weather` has none and is always on); sources of groups switched off in the
  options are not created at all. Sources fail independently: a failing
  source's keys vanish (sensors unknown) and are retried next poll;
  `UpdateFailed` only when no source has data. A source failing for
  `REPAIR_AFTER` (3 h) creates a Repairs issue `source_failing_<source>`,
  deleted on recovery, when its group is switched off, or on entry removal.
  Results are merged into one flat dict, so data keys must stay unique across
  sources (`river_*`, `snow_*`, `today_*`, `yesterday_*`, `year_*`).
- `config_flow.py` — single-instance config flow plus an options flow
  (`groups`, `scan_interval`, `river_warning_level`). Saving options reloads the
  entry (update listener in `__init__.py`).
- `entity.py` — shared base: device info and `unique_id = f"{DOMAIN}_{key}"`.
  Never change a key; it would orphan the user's entity and history.
  `group_for_key()` maps a key **prefix** to its group — a new key must use the
  right prefix or it will not follow its group's on/off option.
  `enabled_descriptions()` filters descriptions and removes registry entries of
  disabled groups.
- `sensor.py` — entity descriptions with `value_fn` and optional `attrs_fn`.
- `brand/` — `icon.png` (256×256) and `icon@2x.png` (512×512), transparent
  corners. Home Assistant serves custom-integration brand images from this
  folder (`homeassistant/components/brands`); missing variants fall back to
  `icon.png`. Rendered from `assets/icon.svg` with
  `magick -background none -density 192 assets/icon.svg -resize 512x512 …`,
  then `-resize 256x256` for `icon.png`; save both with `-depth 8 -strip`.
- `binary_sensor.py` — "Zastareli podatki" (table older than `STALE_AFTER`) and
  "Visok vodostaj Sore" (river level ≥ `river_warning_level` option).
- `diagnostics.py` — options, per-source status and the merged data.
- Translations: `strings.json` and `translations/en.json` must stay identical;
  `translations/sl.json` mirrors their keys (config, options, selector.groups,
  issues.source_failing, entity.sensor states).

## Table vs. header

`parse_weather_html` reads the last `vrstica0`/`vrstica1` row of the data
table. If the table is missing, has no rows, or has fewer than 15 columns, it
falls back to the header line in `<div id="ident">`
(`20,9 °C | 50 % | 12,9 km/h | 0,0 mm`), which yields only `temperature`,
`humidity`, `wind_speed` and `rain_total`. `date`/`time` are filled from the fetch time (`now=`, passed by the
coordinator) so those sensors keep a value, but `measured_at` is **never** set
from it — the stale sensor must not treat fetch time as a measurement.
Other keys the header lacks are **absent**,
not `None`-guessed; sensors show unknown. The result carries `source`
(`"table"`/`"header"`), exposed by the diagnostic
enum sensor `source` ("Vir podatkov"); its state labels live in `strings.json`
and `translations/*.json` under `entity.sensor.source.state`.

## Other pages

- `today.php`, `yesterday.php`, `thisyear.php` — same label / value / when
  table, parsed by `_parse_extremes` with a label → key map per page. Not every
  row has `class="td_data"`, so all `tr`s are scanned. Labels differ between
  pages ("Najvišja dnevna temperatura" vs "Najvišja temperatura"). Year dates
  ("31 julij") get their year from the heading "… v letu 2026".
- River trend — Google Sheet `RIVER_SHEET_URL` (the same one vodostaj.php's JS
  reads): column K = level trend, L = flow trend in the last row that has one
  (`[Narašča]`/`[Pada]`/`[Ustaljen]`); E–G = the chart's warning lines.
- `vodostaj.php` — values are regex-matched in the page text after removing
  scripts; the live trend arrow is filled by JS and is not available.
- `snezna_kamera_ziri.php` — newest-first table; the newest rows are `-`
  placeholders or Google chart iframes, so the first row with a numeric total
  wins. Rows have no year: it comes from the season title (`2025-2026`),
  July–December → first year. Sensors hide values older than `SNOW_MAX_AGE`.

## Tests

`tests/fixtures/tabelaricni_dan_no_rows.html` is a real capture of the page with
an empty table; `..._with_rows.html` is the same page with two synthetic rows.
`today.html`, `yesterday.html`, `thisyear.html`, `vodostaj.html`,
`snezna_kamera_ziri.html` and `river_sheet.txt` are real captures from
2026-10-01. `tests/test_init.py` uses `pytest-homeassistant-custom-component`
(`hass`, `aioclient_mock`, `freeze_time`) to set up the real config entry.

## Releasing

The version lives in **one place**: `version` in
`custom_components/vremenska_postaja_ziri/manifest.json`.

1. Bump `version` (semver — minor for features, patch for fixes).
2. Add a matching `## [x.y.z] - YYYY-MM-DD` entry at the top of `CHANGELOG.md`.
3. Commit, merge to `main`, push (only when the user asks).
4. Tag and publish a GitHub release named `vX.Y.Z` with the changelog entry as
   notes (`gh release create vX.Y.Z --notes "..."`). HACS offers updates based
   on releases; without one it only tracks the latest commit.

## Conventions

- Run tests with `python -m pytest` (needs `pytest-homeassistant-custom-component`;
  `asyncio_mode = "auto"` in `pyproject.toml` is required by its fixtures).
- Conventional Commits (`feat:`, `fix:`, `chore(release):`, …).
- On the default branch, create a feature/release branch before committing.
- Commit or push only when explicitly asked.
