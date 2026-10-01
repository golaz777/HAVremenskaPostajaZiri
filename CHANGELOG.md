# Changelog

All notable changes to Vremenska postaja Žiri are documented here.

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
