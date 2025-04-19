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
__version__ = "1.1.11"

# https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility/13638084#13638084
DETAILED_LEVEL_NUM = 5
logging.addLevelName(DETAILED_LEVEL_NUM, "DETAIL")
def detail(self, message, *args, **kws):
    if self.isEnabledFor(DETAILED_LEVEL_NUM):
        self._log(DETAILED_LEVEL_NUM, message, args, **kws)
logging.Logger.detail = detail
# https://stackoverflow.com/questions/2183233/how-to-add-a-custom-loglevel-to-pythons-logging-facility/13638084#13638084

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

    grpc_client = ChirpGrpc(entry.data, __version__)
    mqtt_client = ChirpToHA(entry.data, __version__, None, grpc_client)

    hass.data[DOMAIN][entry.entry_id] = {
        GRPCLIENT: grpc_client,
        MQTTCLIENT: mqtt_client,
    }

    hass.async_add_executor_job( mqtt_client._client.loop_forever )

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
    _LOGGER.debug(
        "async_unload_entry started"
    )
    _LOGGER.debug(
        "async_unload_entry closed",
    )
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.debug(
        "async_unload_entry platforms %s", unload_ok
    )
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id][MQTTCLIENT].close()
        hass.data[DOMAIN][entry.entry_id][GRPCLIENT].close()
        hass.data[DOMAIN].pop(entry.entry_id)
    _LOGGER.debug(
        "async_unload_entry completed, platform unload return code %s", unload_ok
    )
    return unload_ok
