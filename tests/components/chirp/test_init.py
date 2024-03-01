"""Test the ChirpStack LoRaWan integration initilization path initiated from __init__.py."""
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from tests.components.chirp import common


async def test_entry_setup_unload(hass: HomeAssistant):
    """Test if integration unloads with default configuration."""

    async def run_test_entry_setup_unload(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_setup_unload)
