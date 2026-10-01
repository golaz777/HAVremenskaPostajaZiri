# Vremenska postaja Žiri

A [Home Assistant](https://www.home-assistant.io) custom integration that reads
current weather and air quality from the amateur weather station in Žiri,
Slovenia ([vreme-ziri.si](https://www.vreme-ziri.si/)).

## Features

- Polls the station every 5 minutes
- Temperature, humidity, wind speed/gust/direction, rain rate and daily total,
  pressure, UV index, solar radiation, evapotranspiration and sunshine duration
- PM1, PM2.5, PM10 and AQI (current and last hour) from the station's dust sensor
- **Header fallback.** When the 5-minute data table is empty or can't be read
  (this happens around the start of each month), temperature, humidity, wind
  speed and rainfall are taken from the "Trenutno na meteorološki postaji ŽIRI"
  line in the page header instead of failing with
  *"No data rows found in table"*. Sensors the header does not cover show
  *unknown* until the table is back.
- Single device with all sensors, set up from the UI

## Installation (HACS)

1. In Home Assistant open **HACS**, click the menu (⋮) → **Custom repositories**.
2. Add this URL with type **Integration**:
   ```
   https://github.com/golaz777/HAVremenskaPostajaZiri
   ```
3. Search for **Vremenska postaja Žiri** in HACS and click **Download**.
4. Restart Home Assistant.
5. Go to **Settings → Devices & services → Add integration** and pick
   **Vremenska postaja Žiri**.

### Moving from a manual install

If you previously copied the files into `config/custom_components/vremenska_postaja_ziri`
by hand, just do the HACS steps above. HACS writes to the same folder and the
integration domain is unchanged, so your existing entry, entities and history
stay as they are. Skip step 5.

## Updating

HACS checks for new versions periodically. When one is released it shows up
under **Settings → Updates** (and in HACS). Click **Update**, then restart Home
Assistant.

To check right away: **HACS → ⋮ on the integration → Update information**.

## Sensors

| Sensor | Unit | Header fallback |
|---|---|---|
| Temperatura | °C | ✅ |
| Vlažnost | % | ✅ |
| Hitrost vetra | km/h | ✅ |
| Vsota padavin | mm | ✅ |
| Sunek vetra | km/h | |
| Smer vetra (°) | ° | |
| Prevladujoča smer vetra | text | |
| Jakost padavin | mm/h | |
| Zračni tlak | mbar | |
| UV indeks | | |
| Sončno obsevanje | W/m² | |
| ET izhlapevanje | mm | |
| Trajanje sončnega obsevanja | h | |
| Datum, Čas meritve | text | |
| PM1, PM2.5, PM10 | µg/m³ | n/a (separate source) |
| AIQ-trenutni, AQI-v zadnji uri | | n/a (separate source) |

## Development

```bash
pip install beautifulsoup4 pytest
python -m pytest
```

The HTML parsing lives in `scraper.py`, which has no Home Assistant imports, so
the tests run without Home Assistant installed.

## AI Disclaimer

Parts of this project were developed with assistance from AI tools (Claude by
Anthropic). All code has been reviewed and tested by the author. Use at your
own risk.

## License

MIT
