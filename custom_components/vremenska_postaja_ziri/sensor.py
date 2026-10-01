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
    PERCENTAGE,
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VremenskaPostajaZiriCoordinator
from .const import DOMAIN

@dataclass
class VremenskaPostajaZiriSensorEntityDescription(SensorEntityDescription):
    """Class describing Vremenska postaja Žiri sensor entities."""
    value_fn: Callable[[dict], str | float | None] = None

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
        native_unit_of_measurement="W/m2",
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
        for description in SENSOR_TYPES
    )

class VremenskaPostajaZiriSensor(CoordinatorEntity[VremenskaPostajaZiriCoordinator], SensorEntity):
    """Representation of a Vremenska postaja Žiri sensor."""

    entity_description: VremenskaPostajaZiriSensorEntityDescription

    def __init__(
        self,
        coordinator: VremenskaPostajaZiriCoordinator,
        description: VremenskaPostajaZiriSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, "vremenska_postaja_ziri")},
            name="Vremenska postaja Žiri",
            manufacturer="Vreme Žiri",
            configuration_url="https://www.vreme-ziri.si/tabelaricni_dan.php",
        )

    @property
    def native_value(self) -> str | float | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
