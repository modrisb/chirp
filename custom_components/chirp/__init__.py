"""The Chirpstack LoRaWan integration - setup."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_APPLICATION_ID, DOMAIN, GRPCLIENT, MQTTCLIENT
from .grpc import ChirpGrpc
from .mqtt import ChirpToHA

_LOGGER = logging.getLogger(__name__)

#  List of platforms to support. There should be a matching .py file for each,
#  eg <cover.py> and <sensor.py>
PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PiJups from a config entry."""
    # Store an instance of the "connecting" class that does the work of speaking
    # with your actual devices.
    _LOGGER.debug(
        "async_setup_entry application id %s", entry.data.get(CONF_APPLICATION_ID)
    )
    hass.data.setdefault(DOMAIN, {})

    grpc_client = ChirpGrpc(hass, entry)
    mqtt_client = ChirpToHA(hass, entry, grpc_client)

    hass.data[DOMAIN][entry.entry_id] = {
        GRPCLIENT: grpc_client,
        MQTTCLIENT: mqtt_client,
    }

    mqtt_client.start_bridge()

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
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id][GRPCLIENT].close()
        hass.data[DOMAIN][entry.entry_id][MQTTCLIENT].close()
        hass.data[DOMAIN].pop(entry.entry_id)
    _LOGGER.debug(
        "async_unload_entry completed, platform unload return code %s", unload_ok
    )
    return unload_ok
