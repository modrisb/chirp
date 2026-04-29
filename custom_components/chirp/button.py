"""The ChirpStack LoRaWAN Integration - button implementation."""

import logging

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    BRIDGE_NAME,
    BRIDGE_VENDOR,
    DOMAIN,
    INTEGRATION_DEV_NAME,
    MQTTCLIENT,
    RELOAD_BUTTON,
)

_LOGGER = logging.getLogger(__name__)

BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        # name=RELOAD_BUTTON,
        key=RELOAD_BUTTON,
        translation_key=RELOAD_BUTTON,
        device_class=ButtonDeviceClass.RESTART,
        entity_category=EntityCategory.CONFIG,
        has_entity_name=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Create set-up interface to ChirpStack statistics sensors and add sensors HA."""
    buttons = [ChirpButton(hass, config_entry, button_desc) for button_desc in BUTTONS]
    async_add_entities(buttons, True)
    _LOGGER.debug("async_setup_entry %s buttons added", len(buttons))


async def async_unload():
    """Tear down buttons."""


class ChirpButton(ButtonEntity):
    """Implementation of Chirp reload button."""

    has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self._hass = hass
        self._config = config
        self.entity_description = description
        self._mqtt_client = config.runtime_data[MQTTCLIENT]
        self._attr_name = f"{self.entity_description.key}"
        _LOGGER.debug("self._attr_name %s", self._attr_name)
        self._attr_unique_id = f"{self._config.unique_id}-{self.entity_description.key}"
        _LOGGER.debug("self._attr_unique_id %s", self._attr_unique_id)
        self._available = True
        self._attr_entity_category = self.entity_description.entity_category
        self._attr_device_class = self.entity_description.device_class
        self._attr_device_info: DeviceInfo = DeviceInfo(
            identifiers={(DOMAIN, f"{self._config.unique_id}")},
            name=INTEGRATION_DEV_NAME,
            manufacturer=BRIDGE_VENDOR,
            model=BRIDGE_NAME,
        )

    async def async_press(self) -> None:
        """Reload devices on button press."""
        self._mqtt_client.reload_devices()
