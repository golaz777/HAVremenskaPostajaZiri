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
- `__init__.py` — `DataUpdateCoordinator`; converts `ParseError` to `UpdateFailed`.
- `sensor.py` — entity descriptions; each reads one key from coordinator data.

## Table vs. header

`parse_weather_html` reads the last `vrstica0`/`vrstica1` row of the data
table. If the table is missing, has no rows, or has fewer than 15 columns, it
falls back to the header line in `<div id="ident">`
(`20,9 °C | 50 % | 12,9 km/h | 0,0 mm`), which yields only `temperature`,
`humidity`, `wind_speed` and `rain_total`. Keys the header lacks are **absent**,
not `None`-guessed; sensors show unknown. The result carries `source`
(`"table"`/`"header"`).

`tests/fixtures/tabelaricni_dan_no_rows.html` is a real capture of the page with
an empty table; `..._with_rows.html` is the same page with two synthetic rows.

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

- Run tests with `python -m pytest`. `pyproject.toml` disables the globally installed
  `pytest_homeassistant_custom_component` plugin, whose async autouse fixtures break these tests.
- Conventional Commits (`feat:`, `fix:`, `chore(release):`, …).
- On the default branch, create a feature/release branch before committing.
- Commit or push only when explicitly asked.
