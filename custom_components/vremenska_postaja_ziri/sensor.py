"""Sensor platform for Vremenska postaja Žiri."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    UnitOfIrradiance,
    EntityCategory,
    PERCENTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SNOW_MAX_AGE
from .entity import VremenskaPostajaZiriEntity, enabled_descriptions
from .scraper import COMPASS_POINTS

@dataclass(frozen=True, kw_only=True)
class VremenskaPostajaZiriSensorEntityDescription(SensorEntityDescription):
    """Class describing Vremenska postaja Žiri sensor entities."""
    value_fn: Callable[[dict], str | float | None]
    attrs_fn: Callable[[dict], dict] | None = None


def _today_extreme(
    key: str, name: str, **kwargs
) -> VremenskaPostajaZiriSensorEntityDescription:
    """An extreme with the time it occurred as an attribute (today, yesterday)."""
    kwargs.setdefault("state_class", SensorStateClass.MEASUREMENT)
    return VremenskaPostajaZiriSensorEntityDescription(
        key=key,
        name=name,
        value_fn=lambda data: data.get(key),
        attrs_fn=lambda data: {"time": data.get(f"{key}_time")},
        **kwargs,
    )


def _year_record(
    key: str, name: str, **kwargs
) -> VremenskaPostajaZiriSensorEntityDescription:
    """This year's record, with the date (and time, if known) it was set."""
    kwargs.setdefault("state_class", SensorStateClass.MEASUREMENT)
    return VremenskaPostajaZiriSensorEntityDescription(
        key=key,
        name=name,
        value_fn=lambda data: data.get(key),
        attrs_fn=lambda data: {
            "date": data.get(f"{key}_date"),
            "time": data.get(f"{key}_time"),
            "year": data.get("year"),
        },
        **kwargs,
    )


def _river_attrs(data: dict) -> dict:
    return {"measured_at": data.get("river_measured_at")}


def _snow_value(key: str) -> Callable[[dict], float | None]:
    """Snow value, or None if the latest measurement is too old to be current."""

    def value(data: dict) -> float | None:
        measured = data.get("snow_measured")
        if measured is None or dt_util.now().date() - measured > SNOW_MAX_AGE:
            return None
        return data.get(key)

    return value


def _snow_attrs(data: dict) -> dict:
    return {"measured": data.get("snow_measured"), "notes": data.get("snow_notes")}

SENSOR_TYPES: list[VremenskaPostajaZiriSensorEntityDescription] = [
    VremenskaPostajaZiriSensorEntityDescription(
        key="date",
        name="Datum",
        icon="mdi:calendar",
        value_fn=lambda data: data.get("date"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="time",
        name="Čas meritve",
        icon="mdi:clock",
        value_fn=lambda data: data.get("time"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="temperature",
        name="Temperatura",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("temperature"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="humidity",
        name="Vlažnost",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("humidity"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="wind_speed",
        name="Hitrost vetra",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_speed"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="wind_gust",
        name="Sunek vetra",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_gust"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="wind_direction_deg",
        name="Smer vetra (°)",
        native_unit_of_measurement=DEGREE,
        icon="mdi:compass",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("wind_direction_deg"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="wind_direction",
        name="Smer vetra",
        icon="mdi:compass-rose",
        device_class=SensorDeviceClass.ENUM,
        options=COMPASS_POINTS,
        value_fn=lambda data: data.get("wind_direction"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="rain_rate",
        name="Jakost padavin",
        native_unit_of_measurement="mm/h",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("rain_rate"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="rain_total",
        name="Vsota padavin",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("rain_total"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="pressure",
        name="Zračni tlak",
        native_unit_of_measurement=UnitOfPressure.MBAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("pressure"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="uv_index",
        name="UV indeks",
        icon="mdi:weather-sunny-alert",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("uv_index"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="solar_radiation",
        name="Sončno obsevanje",
        native_unit_of_measurement=UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        device_class=SensorDeviceClass.IRRADIANCE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("solar_radiation"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="et_evaporation",
        name="ET izhlapevanje",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("et_evaporation"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="prevailing_wind_direction",
        name="Prevladujoča smer vetra",
        icon="mdi:compass-outline",
        value_fn=lambda data: data.get("prevailing_wind_direction"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="sunshine_duration",
        name="Trajanje sončnega obsevanja",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("sunshine_duration"),
    ),
    # Today's extremes (today.php)
    _today_extreme(
        "today_temp_max", "Najvišja temperatura danes",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    _today_extreme(
        "today_temp_min", "Najnižja temperatura danes",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    _today_extreme(
        "today_humidity_max", "Najvišja vlažnost danes",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
    ),
    _today_extreme(
        "today_humidity_min", "Najnižja vlažnost danes",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
    ),
    _today_extreme(
        "today_gust_max", "Najmočnejši sunek danes",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
    ),
    _today_extreme(
        "today_wind_max", "Najvišja hitrost vetra danes",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
    ),
    _today_extreme(
        "today_rain_rate_max", "Največja jakost padavin danes",
        native_unit_of_measurement="mm/h",
        device_class=SensorDeviceClass.PRECIPITATION_INTENSITY,
    ),
    _today_extreme(
        "today_rain_hour_max", "Največ padavin v eni uri danes",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
    ),
    _today_extreme(
        "today_pressure_max", "Najvišji zračni tlak danes",
        native_unit_of_measurement=UnitOfPressure.MBAR,
        device_class=SensorDeviceClass.PRESSURE,
    ),
    _today_extreme(
        "today_pressure_min", "Najnižji zračni tlak danes",
        native_unit_of_measurement=UnitOfPressure.MBAR,
        device_class=SensorDeviceClass.PRESSURE,
    ),
    _today_extreme(
        "today_uv_max", "Najvišji UV indeks danes",
        icon="mdi:weather-sunny-alert",
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="dry_spell_days",
        name="Trenutno sušno obdobje",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:weather-sunny",
        value_fn=lambda data: data.get("dry_spell_days"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="rain_spell_days",
        name="Trenutno deževno obdobje",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:weather-rainy",
        value_fn=lambda data: data.get("rain_spell_days"),
    ),
    # Yesterday (yesterday.php)
    _today_extreme(
        "yesterday_temp_max", "Najvišja temperatura včeraj",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    _today_extreme(
        "yesterday_temp_min", "Najnižja temperatura včeraj",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    _today_extreme(
        "yesterday_rain", "Padavine včeraj",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
    ),
    _today_extreme(
        "yesterday_gust_max", "Najmočnejši sunek včeraj",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
    ),
    # This year's records (thisyear.php)
    _year_record(
        "year_temp_max", "Najvišja temperatura letos",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    _year_record(
        "year_temp_min", "Najnižja temperatura letos",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    _year_record(
        "year_rain", "Padavine letos",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    _year_record(
        "year_rain_day_max", "Največ padavin v enem dnevu letos",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
    ),
    _year_record(
        "year_rain_hour_max", "Največ padavin v eni uri letos",
        native_unit_of_measurement=UnitOfLength.MILLIMETERS,
        device_class=SensorDeviceClass.PRECIPITATION,
    ),
    _year_record(
        "year_gust_max", "Najmočnejši sunek letos",
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        device_class=SensorDeviceClass.WIND_SPEED,
    ),
    _year_record(
        "year_dry_spell_max", "Najdaljše sušno obdobje letos",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:weather-sunny",
        state_class=None,
    ),
    _year_record(
        "year_rain_spell_max", "Najdaljše deževno obdobje letos",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:weather-rainy",
        state_class=None,
    ),
    # River Sora (vodostaj.php)
    VremenskaPostajaZiriSensorEntityDescription(
        key="river_level_trend",
        name="Trend vodostaja Sore",
        translation_key="river_trend",
        icon="mdi:trending-up",
        device_class=SensorDeviceClass.ENUM,
        options=["rising", "falling", "steady"],
        value_fn=lambda data: data.get("river_level_trend"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="river_flow_trend",
        name="Trend pretoka Sore",
        translation_key="river_trend",
        icon="mdi:trending-up",
        device_class=SensorDeviceClass.ENUM,
        options=["rising", "falling", "steady"],
        value_fn=lambda data: data.get("river_flow_trend"),
    ),
    # River Sora (vodostaj.php)
    VremenskaPostajaZiriSensorEntityDescription(
        key="river_level",
        name="Vodostaj Sore",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:waves",
        value_fn=lambda data: data.get("river_level"),
        attrs_fn=_river_attrs,
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="river_flow",
        name="Pretok Sore",
        native_unit_of_measurement="m³/s",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:waves-arrow-right",
        value_fn=lambda data: data.get("river_flow"),
        attrs_fn=lambda data: {
            **_river_attrs(data),
            "description": data.get("river_flow_class"),
        },
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="river_temperature",
        name="Temperatura Sore",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("river_temperature"),
        attrs_fn=_river_attrs,
    ),
    # Snow (snezna_kamera_ziri.php), measured by hand at 7:00
    VremenskaPostajaZiriSensorEntityDescription(
        key="snow_depth",
        name="Višina snega",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:snowflake",
        value_fn=_snow_value("snow_depth"),
        attrs_fn=_snow_attrs,
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="snow_new",
        name="Novozapadli sneg",
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:snowflake-alert",
        value_fn=_snow_value("snow_new"),
        attrs_fn=_snow_attrs,
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="source",
        name="Vir podatkov",
        translation_key="source",
        icon="mdi:database-search",
        device_class=SensorDeviceClass.ENUM,
        options=["table", "header"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.get("source"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="valPM1",
        name="PM1",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM1,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("valPM1"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="valPM25",
        name="PM2.5",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM25,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("valPM25"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="valPM10",
        name="PM10",
        native_unit_of_measurement=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        device_class=SensorDeviceClass.PM10,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("valPM10"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="valAQI",
        name="AIQ-trenutni",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("valAQI"),
    ),
    VremenskaPostajaZiriSensorEntityDescription(
        key="valAQI1h",
        name="AQI-v zadnji uri",
        device_class=SensorDeviceClass.AQI,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("valAQI1h"),
    ),
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        VremenskaPostajaZiriSensor(coordinator, description)
        for description in enabled_descriptions(hass, entry, "sensor", SENSOR_TYPES)
    )

class VremenskaPostajaZiriSensor(VremenskaPostajaZiriEntity, SensorEntity):
    """Representation of a Vremenska postaja Žiri sensor."""

    entity_description: VremenskaPostajaZiriSensorEntityDescription

    @property
    def native_value(self) -> str | float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return extra attributes, e.g. when today's extreme occurred."""
        if self.entity_description.attrs_fn is None or self.coordinator.data is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
