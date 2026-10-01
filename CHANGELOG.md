# Changelog

All notable changes to Vremenska postaja Žiri are documented here.

## [1.2.0] - 2026-10-01

### Added
- **Vir podatkov** diagnostic sensor showing where the weather values come
  from: `table` (Tabela) or `header` (Glava strani, the fallback). It is an
  enum sensor, so automations can trigger on it.
- **River Sora** sensors: water level (cm), flow (m³/s, with the site's
  description such as *mali pretok*) and water temperature.
- **Snow** sensors: total depth and fresh snow from the daily 7:00 measurement.
  Measurements older than 3 days show *unknown* rather than a stale value.
- **Today's extremes**: max/min temperature, humidity and pressure, strongest
  gust, max 10-minute wind, heaviest rain rate, most rain in an hour, max UV —
  each with a `time` attribute — and the current dry and rainy spell in days.
- **Smer vetra** sensor with the wind direction as a compass point.
- **Zastareli podatki** problem sensor, on when the newest table row is more
  than 30 minutes old.

### Changed
- Every page is now fetched and fails independently. Previously a failure in
  the weather table also skipped the PM/AQI fetch. Slow-changing pages are
  fetched less often (today's extremes and river every 15 min, snow hourly).
- Requests use Home Assistant's shared HTTP session, and HTML parsing runs off
  the event loop.

### Fixed
- **Sončno obsevanje** used the unit `W/m2`, which Home Assistant rejects for
  irradiance; it is now `W/m²`. Home Assistant may ask you to confirm the unit
  change for long-term statistics under Developer tools → Statistics.

## [1.1.0] - 2026-10-01

### Added
- **Header fallback.** When the 5-minute data table is missing, empty
  (*"No data rows found in table"*, typical at the start of a month) or has an
  unexpected layout, temperature, humidity, wind speed and rainfall are read
  from the current-values line in the page header instead of the update
  failing. The other weather sensors show *unknown* until the table returns.
  A log line at info level marks each switch between table and header.
- Installable and updatable through **HACS** as a custom repository.
- Slovenian and English translations for the setup dialog.

### Changed
- Repository restructured to the HACS layout
  (`custom_components/vremenska_postaja_ziri/`). The integration domain is
  unchanged, so existing installs keep their entities and history.
- `beautifulsoup4` is now declared in the manifest requirements.

## [1.0.0] - 2025

### Added
- Initial release: weather sensors from vreme-ziri.si and PM/AQI sensors from
  the station's dust sensor.
