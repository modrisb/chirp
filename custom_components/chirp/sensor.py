"""The Chirpstack LoRaWan integration - sensor implementation."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BRIDGE_NAME,
    BRIDGE_VENDOR,
    DOMAIN,
    INTEGRATION_DEV_NAME,
    MQTTCLIENT,
    STATISTICS_DEVICES,
    STATISTICS_SENSORS,
    STATISTICS_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

SENSORS = [
    SensorEntityDescription(
        STATISTICS_SENSORS,
        name="Total number of sensors",
        has_entity_name=True,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key=STATISTICS_SENSORS,
    ),
    SensorEntityDescription(
        STATISTICS_DEVICES,
        name="Total number of devices",
        has_entity_name=True,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key=STATISTICS_DEVICES,
    ),
    SensorEntityDescription(
        STATISTICS_UPDATED,
        name="Sensor update on",
        has_entity_name=True,
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key=STATISTICS_UPDATED,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create set-up interface to UPS and add sensors for passed config_entry in HA."""
    sensors = [ChirpSensor(hass, config_entry, sensor_desc) for sensor_desc in SENSORS]
    async_add_entities(sensors, True)
    _LOGGER.debug("async_setup_entry %s sensors added", len(sensors))


class ChirpSensor(SensorEntity):
    """Implementation of Chirp sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self._hass = hass
        self._config = config
        self.entity_description = description
        self._mqtt_client = hass.data[DOMAIN][self._config.entry_id][MQTTCLIENT]
        self._attr_name = self.entity_description.name
        self._available = True
        self._attr_state_class = self.entity_description.state_class
        self._attr_device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, self._config.unique_id)},
            name=INTEGRATION_DEV_NAME,
            manufacturer=BRIDGE_VENDOR,
            model=BRIDGE_NAME,
        )

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._config.unique_id + "_" + self.entity_description.key

    async def async_update(self):
        """Update sensor values/states."""
        self._attr_native_value = self._mqtt_client.get_sensor_statistics()[
            self.entity_description.key
        ]
