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

from .const import DEVICE_INFO, MQTTCLIENT, RELOAD_BUTTON

_LOGGER = logging.getLogger(__name__)

BUTTONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key=RELOAD_BUTTON,
        translation_key=RELOAD_BUTTON,
        device_class=ButtonDeviceClass.UPDATE,
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

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()
        self.entity_description = description
        self._mqtt_client = config.runtime_data[MQTTCLIENT]
        self._attr_unique_id = f"{config.unique_id}_{self.entity_description.key}"
        self._attr_device_info: DeviceInfo = DEVICE_INFO[0]


    async def async_press(self) -> None:
        """Reload devices on button press."""
        self._mqtt_client.reload_devices()
