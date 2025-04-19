"""Common routines/constants for bridge tests."""
from unittest import mock
import asyncio
import re

from homeassistant.components.chirp.config_flow import generate_unique_id
from homeassistant.components.chirp.const import (
    CONF_API_KEY,
    CONF_API_PORT,
    CONF_API_SERVER,
    CONF_APPLICATION,
    CONF_APPLICATION_ID,
    CONF_MQTT_DISC,
    CONF_MQTT_PORT,
    CONF_MQTT_PWD,
    CONF_MQTT_SERVER,
    CONF_MQTT_USER,
    CONF_OPTIONS_DEBUG_PAYLOAD,
    CONF_OPTIONS_RESTORE_AGE,
    CONF_OPTIONS_START_DELAY,
    CONF_TENANT,
    DEFAULT_OPTIONS_DEBUG_PAYLOAD,
    DEFAULT_OPTIONS_RESTORE_AGE,
    DEFAULT_OPTIONS_START_DELAY,
    DOMAIN,
    MQTTCLIENT,
)
from homeassistant.core import HomeAssistant
from tests.common import MockConfigEntry

from .patches import api, grpc, message, mqtt, set_size

DEF_API_KEY = "apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0apikey0"

CONFIG_DATA = {
    CONF_API_SERVER: "localhost",
    CONF_API_PORT: 8080,
    CONF_API_KEY: DEF_API_KEY,
    CONF_TENANT: "TenantName0",
    CONF_APPLICATION: "ApplicationName0",
    CONF_APPLICATION_ID: "ApplicationId0",
    CONF_MQTT_SERVER: "localhost",
    CONF_MQTT_PORT: 1883,
    CONF_MQTT_USER: "user",
    CONF_MQTT_PWD: "pwd",
    CONF_MQTT_DISC: "ha",
}

CONFIG_OPTIONS = {
    CONF_OPTIONS_START_DELAY: 0, #DEFAULT_OPTIONS_START_DELAY,
    CONF_OPTIONS_RESTORE_AGE: 0, #DEFAULT_OPTIONS_RESTORE_AGE,
    CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
}

# pytest tests/components/chirp/
# pytest tests/components/chirp/ --cov=homeassistant.components.chirp --cov-report term-missing -vv


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
async def chirp_setup_and_run_test(
    hass: HomeAssistant, expected_entry_setup, run_test_case, debug_payload=False
):
    """Execute test case in standard configuration environment with grpc/mqtt mocks."""

    set_size()
    config_options = CONFIG_OPTIONS.copy()
    config_options[CONF_OPTIONS_DEBUG_PAYLOAD] = debug_payload
    unique_id = generate_unique_id(CONFIG_DATA)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=unique_id,
        data=CONFIG_DATA,
        options=config_options,
    )

    # Load config_entry.
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id) == expected_entry_setup

    mqtt_client = hass.data[DOMAIN][entry.entry_id][MQTTCLIENT]
    mqtt_client._client.on_message(
        mqtt_client._client,
        None,
        message(f"{entry.data.get(CONF_MQTT_DISC)}/status", "online"),
    )

    mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).wait_empty_queue()
    await hass.async_block_till_done()
    #await asyncio.sleep(0.5)

    if expected_entry_setup:
        await run_test_case(hass, entry)

    await hass.config_entries.async_unload(entry.entry_id)


async def reload_devices(hass: HomeAssistant, config):
    """Reload devices from ChirpStack server and wait for activity completion."""
    await hass.async_block_till_done()
    mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).publish(f"application/{config.data.get(CONF_APPLICATION_ID)}/bridge/restart","")
    mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).wait_empty_queue()
    await hass.async_block_till_done()
    #await asyncio.sleep(0.5)

def count_messages(topic, payload, keep_history=False):
    """Count posted mqtt messages that matche topic and payload filters."""
    messages = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published(keep_history=keep_history)
    count = 0
    for message in messages:
        mi_topic = re.search(topic, message[0])
        if payload:
            if message[1]:
                mi_payload = re.search(payload, message[1])
                if mi_topic and mi_payload:
                    count += 1
        else:
            if mi_topic:
                count += 1

    return count

def count_messages_with_no_payload(topic, keep_history=False):
    """Count posted mqtt messages that matche topic and payload filters."""
    messages = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published(keep_history=keep_history)
    count = 0
    for message in messages:
        mi_topic = re.search(topic, message[0])
        if mi_topic and not message[1]:
            count += 1
    return count
