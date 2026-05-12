"""The ChirpStack LoRaWAN Integration - setup."""

from __future__ import annotations

import logging

from pychirpha.const import BRIDGE_NAME, BRIDGE_VENDOR, CLASSES, CONF_APPLICATION_ID
from pychirpha.grpc import ChirpGrpc
from pychirpha.mqtt import ChirpToHA

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DEVICE_INFO,
    DOMAIN,
    GRPCLIENT,
    INTEGRATION_DEV_NAME,
    INTEGRATION_DEV_TRANSLATION_KEY,
    MQTTCLIENT,
)

_LOGGER = logging.getLogger(__name__)
__version__ = "1.2.0"

#  List of platforms to support. There should be a matching .py file for each,
#  eg <cover.py> and <sensor.py>
PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.SENSOR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Chirp from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    _LOGGER.debug(
        "async_setup_entry application id %s", entry.data.get(CONF_APPLICATION_ID)
    )

    DEVICE_INFO.append(DeviceInfo(
            identifiers={(DOMAIN, f"{entry.unique_id}")},
            name=INTEGRATION_DEV_NAME,
            manufacturer=BRIDGE_VENDOR,
            model=BRIDGE_NAME,
            translation_key=INTEGRATION_DEV_TRANSLATION_KEY,
        )
    )

    grpc_client = ChirpGrpc(entry.data, __version__)
    mqtt_client = ChirpToHA(entry.data, __version__, CLASSES, grpc_client)

    entry.runtime_data = {
        GRPCLIENT: grpc_client,
        MQTTCLIENT: mqtt_client,
    }

    await hass.async_add_executor_job(mqtt_client._client.loop_start)  # noqa: SLF001

    # This creates each HA object for each platform your device requires.
    # It's done by calling the `async_setup_entry` function in each platform module.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("async_setup_entry completed")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when an entry/configured device is to be removed. The class
    # needs to unload itself, and remove callbacks. See the classes for further
    # details
    _LOGGER.debug("async_unload_entry started")

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug("async_unload_entry platforms %s", unload_ok)
    if unload_ok:
        if entry.runtime_data:
            entry.runtime_data[MQTTCLIENT].close()
            entry.runtime_data[GRPCLIENT].close()
            entry.runtime_data = None
    _LOGGER.debug(
        "async_unload_entry completed, platform unload return code %s", unload_ok
    )
    return unload_ok
