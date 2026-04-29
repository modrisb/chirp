"""The ChirpStack LoRaWAN Integration - sensor implementation."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

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

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=STATISTICS_SENSORS,
        # name=STATISTICS_SENSORS,
        has_entity_name=True,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key=STATISTICS_SENSORS,
    ),
    SensorEntityDescription(
        key=STATISTICS_DEVICES,
        # name=STATISTICS_DEVICES,
        has_entity_name=True,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key=STATISTICS_DEVICES,
    ),
    SensorEntityDescription(
        key=STATISTICS_UPDATED,
        # name=STATISTICS_UPDATED,
        has_entity_name=True,
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key=STATISTICS_UPDATED,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create set-up interface to ChirpStack statistics sensors and add sensors HA."""
    sensors = [ChirpSensor(hass, config_entry, sensor_desc) for sensor_desc in SENSORS]
    async_add_entities(sensors, True)
    _LOGGER.debug("async_setup_entry %s sensors added", len(sensors))


async def async_unload():
    """Tear down sensors."""


class ChirpSensor(SensorEntity):
    """Implementation of Chirp statistics sensor."""

    _attr_has_entity_name = True

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
        self._mqtt_client = config.runtime_data[MQTTCLIENT]
        self._attr_name = f"{self.entity_description.key}"
        self._attr_unique_id = f"{self._config.unique_id}-{self.entity_description.key}"
        self._attr_entity_category = description.entity_category
        self._attr_device_class = description.device_class
        self._available = True
        self._attr_state_class = self.entity_description.state_class
        self._attr_device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, f"{self._config.unique_id}")},
            name=INTEGRATION_DEV_NAME,
            manufacturer=BRIDGE_VENDOR,
            model=BRIDGE_NAME,
        )

    async def async_update(self) -> None:
        """Update sensor values/states."""
        if self.entity_description.key == STATISTICS_SENSORS:
            self._attr_native_value = self._mqtt_client.dev_sensor_count
        elif self.entity_description.key == STATISTICS_DEVICES:
            self._attr_native_value = self._mqtt_client.dev_count
        elif self.entity_description.key == STATISTICS_UPDATED:
            self._attr_native_value = self._mqtt_client.last_update
