"""Test the ChirpStack LoRaWAN integration initialization path initiated from __init__.py."""

import logging
import pathlib
from unittest import mock

import pytest

from homeassistant.components.chirp.__init__ import DETAILED_LEVEL_NUM
from homeassistant.components.chirp.const import (
    BRIDGE_CONF_COUNT,
    CONF_MQTT_CHIRPSTACK_PREFIX,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .patches import api, get_size, grpc, mqtt, set_size

from tests.components.chirp import common


@pytest.fixture(autouse=True)
def cleanup():
    """Reset mock settings and close mqtt connection if needed."""
    mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).reset_mock()    #   default mock settings
    yield
    # teardown - close mqtt connection if needed
    mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).reset_mock()    #   default mock settings

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

        messages = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published(keep_history=True)
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


async def test_empty_chirpstack_prefix(hass: HomeAssistant):
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

async def test_no_classes_file(hass: HomeAssistant, caplog):
    """Test if integration unloads with default configuration."""

    async def run_test_no_classes_file(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED

        await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

        configs = common.count_messages(
            r"/config$", r"/application", keep_history=True
        )  # to be received as subscribed
        assert configs == 0

    original_with_name = pathlib.Path.with_name
    new_with_name = lambda file_name: original_with_name("fixed_b")  # noqa: E731

    with mock.patch("pathlib.Path.with_name",  new_with_name):
        await common.chirp_setup_and_run_test(hass, True, run_test_no_classes_file)

    assert "File classes.json not loaded, device class defaults might be affected" in caplog.text


async def test_detail_log_level(hass: HomeAssistant, caplog):
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
