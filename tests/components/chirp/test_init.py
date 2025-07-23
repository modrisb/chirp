"""Test the ChirpStack LoRaWAN integration initilization path initiated from __init__.py."""
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from tests.components.chirp import common
from homeassistant.components.chirp.const import (
    CONF_MQTT_CHIRPSTACK_PREFIX,
    BRIDGE_CONF_COUNT,
)
from .patches import get_size, message, mqtt, set_size

async def test_entry_setup_unload(hass: HomeAssistant):
    """Test if integration unloads with default configuration."""

    async def run_test_entry_setup_unload(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_setup_unload)

async def test_non_empty_chirpstack_prefix(hass: HomeAssistant):
    """Test if integration unloads with default configuration."""

    chirpstack_prefix = r"xStack_prefix_for_test"
    async def run_test_entry_setup_unload(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

        configs = common.count_messages(r'/config$', chirpstack_prefix+r'/application', keep_history=True)    # to be received as subscribed
        assert configs == BRIDGE_CONF_COUNT + get_size("sensors") * get_size("idevices")

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_setup_unload, config_data={CONF_MQTT_CHIRPSTACK_PREFIX:chirpstack_prefix})


async def test_empty_chirpstack_prefix(hass: HomeAssistant):
    """Test if integration unloads with default configuration."""

    async def run_test_entry_setup_unload(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

        configs = common.count_messages(r'/config$', r'/application', keep_history=True)    # to be received as subscribed
        assert configs == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_setup_unload)
