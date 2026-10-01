<img src="custom_components/vremenska_postaja_ziri/brand/icon.png" alt="" width="96" align="right">

# Vremenska postaja Žiri

A [Home Assistant](https://www.home-assistant.io) custom integration that reads
current weather and air quality from the amateur weather station in Žiri,
Slovenia ([vreme-ziri.si](https://www.vreme-ziri.si/)).

## Features

- Polls the station every 5 minutes (configurable, 5–60)
- Temperature, humidity, wind speed/gust/direction, rain rate and daily total,
  pressure, UV index, solar radiation, evapotranspiration and sunshine duration
- PM1, PM2.5, PM10 and AQI (current and last hour) from the station's dust sensor
- **River Sora** water level, flow, temperature and rising/falling trend, plus
  a **high-water warning** sensor with a level you choose
- **Snow depth** and fresh snow from the daily 7:00 manual measurement
- **Today's extremes** — max/min temperature, humidity and pressure, strongest
  gust, heaviest rain, max UV, each with the time it happened, plus the current
  dry and rainy spell in days
- **Yesterday's** max/min temperature, rain and strongest gust, and **this
  year's records** (hottest, coldest, wettest day, strongest gust, longest dry
  and rainy spell, …) with the date they were set
- **Options** to switch off data you don't need, so fewer pages are fetched
- Wind direction as a compass point (S, SSV, … in Slovenian notation)
- **Stale data** problem sensor that turns on when the 5-minute table stops updating
- Each page is fetched and fails on its own, so e.g. a broken dust-sensor sheet
  never takes the weather sensors down with it. If a page keeps failing for 3
  hours, a warning appears under **Settings → Repairs**
- **Diagnostics download** showing what was last read from every page
- **Header fallback.** When the 5-minute data table is empty or can't be read
  (this happens around the start of each month), temperature, humidity, wind
  speed and rainfall are taken from the "Trenutno na meteorološki postaji ŽIRI"
  line in the page header instead of failing with
  *"No data rows found in table"*. **Datum** and **Čas meritve** then show
  when the page was fetched, since the header has no timestamp of its own.
  Sensors the header does not cover show *unknown* until the table is back.
  The diagnostic sensor **Vir podatkov** shows which source is in use, so
  you can see it on a dashboard or use it in automations.
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

## Options

**Settings → Devices & services → Vremenska postaja Žiri → Configure**

| Option | Default | Description |
|---|---|---|
| Data groups | all | Today's extremes, Yesterday, This year's records, River Sora, Snow, Air quality. The 5-minute weather table is always read. Sensors of groups you switch off are removed, and come back when you switch the group on again |
| Weather update interval | 5 min | How often the weather table and air-quality sheet are read (5–60). The other pages have their own, slower schedule |
| River Sora warning level | 200 cm | **Visok vodostaj Sore** turns on at or above this level. The site's river chart draws warning lines at 200, 240 and 280 cm |

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
| Smer vetra | S, SSV, SV, … | |
| Datum, Čas meritve | text | ✅ time of fetch |
| PM1, PM2.5, PM10 | µg/m³ | n/a (separate source) |
| AIQ-trenutni, AQI-v zadnji uri | | n/a (separate source) |
| Vir podatkov (diagnostic) | Tabela / Glava strani | shows which source is in use |
| Zastareli podatki (diagnostic, binary) | on / off | unknown while on header fallback |

### Today's extremes (`today.php`, every 15 min)

Each has a `time` attribute with when it happened (HH:MM).

| Sensor | Unit |
|---|---|
| Najvišja / Najnižja temperatura danes | °C |
| Najvišja / Najnižja vlažnost danes | % |
| Najmočnejši sunek danes, Najvišja hitrost vetra danes | km/h |
| Največja jakost padavin danes | mm/h |
| Največ padavin v eni uri danes | mm |
| Najvišji / Najnižji zračni tlak danes | mbar |
| Najvišji UV indeks danes | |
| Trenutno sušno / deževno obdobje | days |

### Yesterday (`yesterday.php`, hourly)

Each has a `time` attribute (HH:MM), except the rain total.

| Sensor | Unit |
|---|---|
| Najvišja / Najnižja temperatura včeraj | °C |
| Padavine včeraj | mm |
| Najmočnejši sunek včeraj | km/h |

### This year's records (`thisyear.php`, hourly)

Each has a `date` attribute (and `time`, where the site gives one).

| Sensor | Unit |
|---|---|
| Najvišja / Najnižja temperatura letos | °C |
| Padavine letos | mm |
| Največ padavin v enem dnevu letos, Največ padavin v eni uri letos | mm |
| Najmočnejši sunek letos | km/h |
| Najdaljše sušno / deževno obdobje letos | days |

### River Sora (`vodostaj.php` and its data sheet, every 15 min)

| Sensor | Unit | Attributes |
|---|---|---|
| Vodostaj Sore | cm | `measured_at` |
| Pretok Sore | m³/s | `measured_at`, `description` (e.g. *mali pretok*) |
| Temperatura Sore | °C | `measured_at` |
| Trend vodostaja Sore, Trend pretoka Sore | Narašča / Pada / Ustaljen | |
| Visok vodostaj Sore (binary, safety) | on = unsafe | `level`, `threshold`, `trend`, `site_warning_levels`, `measured_at` |

The site publishes river data roughly hourly, so `measured_at` can trail the
current time by an hour or more.

### Snow (`snezna_kamera_ziri.php`, hourly)

| Sensor | Unit | Attributes |
|---|---|---|
| Višina snega | cm | `measured` (date), `notes` |
| Novozapadli sneg | cm / 24 h | `measured` (date), `notes` |

Snow is measured by hand at 7:00. If the latest measurement is more than 3
days old (all summer, for example) the sensors show *unknown* instead of last
season's value; the `measured` attribute still shows when it was taken.

### Example: flood alert

Set the warning level under **Options**, then:

```yaml
automation:
  - alias: Sora flood warning
    triggers:
      - trigger: state
        entity_id: binary_sensor.vremenska_postaja_ziri_visok_vodostaj_sore
        to: "on"
    actions:
      - action: notify.notify
        data:
          message: >
            Sora is at {{ state_attr('binary_sensor.vremenska_postaja_ziri_visok_vodostaj_sore', 'level') }} cm
            and {{ states('sensor.vremenska_postaja_ziri_trend_vodostaja_sore') }}
```

Entity IDs depend on your setup; check yours under **Settings → Entities**.

## Troubleshooting

- **A warning under Settings → Repairs** means one page of vreme-ziri.si has
  not been readable for 3 hours. It clears itself when the page works again.
  If you don't need that data, switch its group off in **Options**.
- **Download diagnostics** (integration page → ⋮ → *Download diagnostics*)
  shows, for every page, when it was last read, the current error if any, and
  all values the integration currently has. Attach it to bug reports.

## Development

```bash
pip install pytest-homeassistant-custom-component
python -m pytest
```

The HTML parsing lives in `scraper.py`, which has no Home Assistant imports, and
is tested against real page captures in `tests/fixtures/`. `tests/test_init.py`
sets the integration up in a test Home Assistant instance with mocked pages.

## AI Disclaimer

Parts of this project were developed with assistance from AI tools (Claude by
Anthropic). All code has been reviewed and tested by the author. Use at your
own risk.

## License

MIT
