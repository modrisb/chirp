"""Test the ChirpStack LoRaWAN integration reload devices button press."""

import asyncio

from pychirpha.mqtt import ChirpToHA
import pytest

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.chirp.const import DOMAIN, MQTTCLIENT
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant

from . import common
from .patches import get_size, mqtt, set_size


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


async def test_devices_reload_button_press(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test if button press re-loads devices."""

    async def run_test_devices_reload_button_press(hass: HomeAssistant, entry):
        assert entry.state is ConfigEntryState.LOADED
        mqtt_client: ChirpToHA = entry.runtime_data[MQTTCLIENT]
        initial_last_update = mqtt_client.last_update
        initial_dev_count = mqtt_client.dev_count
        initial_dev_sensor_count = mqtt_client.dev_sensor_count
        mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).wait_empty_queue()
        await hass.async_block_till_done()
        entity_ids = hass.states.async_entity_ids(BUTTON_DOMAIN)  # (BUTTON_DOMAIN)
        assert len(entity_ids) >= 1
        await asyncio.sleep(0.01)
        set_size(devices=get_size("devices") + 1)
        for entity_id in entity_ids:
            await hass.services.async_call(
                BUTTON_DOMAIN,
                SERVICE_PRESS,
                {ATTR_ENTITY_ID: entity_id},
                blocking=True,
            )
        after_reload_last_update = mqtt_client.last_update
        after_reload_dev_count = mqtt_client.dev_count
        after_reload_dev_sensor_count = mqtt_client.dev_sensor_count

        await hass.config_entries.async_unload(entry.entry_id)

        assert initial_last_update < after_reload_last_update
        assert initial_dev_count < after_reload_dev_count
        assert initial_dev_sensor_count < after_reload_dev_sensor_count

        assert entry.state is ConfigEntryState.NOT_LOADED

    await common.chirp_setup_and_run_test(
        hass, True, run_test_devices_reload_button_press
    )
    assert "Devices reloaded, " in caplog.text
