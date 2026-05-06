"""Test the ChirpStack LoRaWAN integration initialization path initiated from __init__.py."""

import pathlib
from unittest import mock

from pychirpha.const import (
    BRIDGE_CONF_COUNT,
    CONF_MQTT_CHIRPSTACK_PREFIX,
    DETAILED_LEVEL_NUM,
)
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from . import common
from .patches import get_size, mqtt


@pytest.fixture(autouse=True)
def cleanup():
    """Reset mock settings and close mqtt connection if needed."""
    mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    ).reset_mock()  #   default mock settings
    yield
    # teardown - close mqtt connection if needed
    mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2
    ).reset_mock()  #   default mock settings


async def test_entry_setup_unload(hass: HomeAssistant) -> None:
    """Test if integration unloads with default configuration."""

    async def run_test_entry_setup_unload(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_setup_unload)


async def test_non_empty_chirpstack_prefix(hass: HomeAssistant) -> None:
    """Test if integration unloads with default configuration."""

    chirpstack_prefix = r"xStack_prefix_for_test"

    async def run_test_entry_setup_unload(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

        mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published(keep_history=True)
        configs = common.count_messages(
            r"/config$", chirpstack_prefix + r"/application", keep_history=True
        )  # to be received as subscribed
        assert configs == BRIDGE_CONF_COUNT + get_size("sensors") * get_size("idevices")

    await common.chirp_setup_and_run_test(
        hass,
        True,
        run_test_entry_setup_unload,
        config_data={CONF_MQTT_CHIRPSTACK_PREFIX: chirpstack_prefix},
    )


async def test_empty_chirpstack_prefix(hass: HomeAssistant) -> None:
    """Test if integration unloads with default configuration."""

    async def run_test_entry_setup_unload(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

        configs = common.count_messages(
            r"/config$", r"/application", keep_history=True
        )  # to be received as subscribed
        assert configs == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_setup_unload)


async def test_detail_log_level(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test if integration unloads with default configuration."""

    caplog.set_level(DETAILED_LEVEL_NUM)

    async def run_test_detail_log_level(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

        configs = common.count_messages(
            r"/config$", r"/application", keep_history=True
        )  # to be received as subscribed
        assert configs == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_detail_log_level)

    detail_count = 0
    for record_tuple in caplog.record_tuples:
        if record_tuple[1] == DETAILED_LEVEL_NUM:
            detail_count = detail_count + 1
    assert detail_count > 0
