"""Common routines/constants for bridge tests."""
from unittest import mock

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

CONFIG_DATA = {
    CONF_API_SERVER: "localhost",
    CONF_API_PORT: 8080,
    CONF_API_KEY: "apikey0",
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
    CONF_OPTIONS_START_DELAY: DEFAULT_OPTIONS_START_DELAY,
    CONF_OPTIONS_RESTORE_AGE: DEFAULT_OPTIONS_RESTORE_AGE,
    CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
}

# pytest tests/components/pijups/
# pytest tests/components/pijups/ --cov=homeassistant.components.pijups --cov-report term-missing -vv


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

    if expected_entry_setup:
        await run_test_case(hass, entry)


async def reload_devices(hass: HomeAssistant, config):
    """Reload devices from ChirpStack server and wait for activity completion."""
    await hass.async_block_till_done()
    restart_topic = f"application/{config.data.get(CONF_APPLICATION_ID)}/bridge/restart"
    mqtt.Client().reset_stats()
    mqtt.Client().on_message(mqtt.Client(), None, message(restart_topic, ""))
    await hass.async_block_till_done()
