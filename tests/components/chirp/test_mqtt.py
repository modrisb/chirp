"""Test the ChirpStack LoRa integration MQTT integration class."""

import time

from homeassistant.components.chirp.const import BRIDGE_CONF_COUNT, CONF_APPLICATION_ID
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from tests.components.chirp import common

from .patches import get_size, message, mqtt, set_size


async def test_extended_debug_level(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_level_names_with_indexes(
        hass: HomeAssistant, config: ConfigEntry
    ):
        await hass.async_block_till_done()
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == get_size("devices")
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("devices") * get_size("sensors")

    await common.chirp_setup_and_run_test(
        hass, True, run_test_level_names_with_indexes, True
    )


async def test_level_names_with_indexes(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_level_names_with_indexes(
        hass: HomeAssistant, config: ConfigEntry
    ):
        await hass.async_block_till_done()
        set_size(codec=5)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == get_size("devices")
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("devices") * get_size("sensors")

    await common.chirp_setup_and_run_test(hass, True, run_test_level_names_with_indexes)


async def test_values_template_default(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_values_template_default(
        hass: HomeAssistant, config: ConfigEntry
    ):
        await hass.async_block_till_done()
        set_size(codec=6)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == get_size("devices")
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("devices") * get_size("sensors")

    await common.chirp_setup_and_run_test(hass, True, run_test_values_template_default)


async def test_explicit_integration_setting(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_values_template_default(
        hass: HomeAssistant, config: ConfigEntry
    ):
        await hass.async_block_till_done()
        set_size(codec=7)
        await common.reload_devices(hass, config)
        assert get_size("devices") * get_size("sensors") == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors

    await common.chirp_setup_and_run_test(hass, True, run_test_values_template_default)


async def test_no_device_class(hass: HomeAssistant):  #######
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_no_device_class(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(codec=8)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("devices")

    await common.chirp_setup_and_run_test(hass, True, run_test_no_device_class)


async def test_wrong_device_class(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_wrong_device_class(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(codec=9)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("devices")

    await common.chirp_setup_and_run_test(hass, True, run_test_wrong_device_class)


async def test_command_topic(hass: HomeAssistant):  ########
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_command_topic(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(codec=10)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("devices")

    await common.chirp_setup_and_run_test(hass, True, run_test_command_topic)


async def test_humidifier_dev_class(hass: HomeAssistant):  ########
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_humidifier_dev_class(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(codec=15)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("devices")

    await common.chirp_setup_and_run_test(hass, True, run_test_humidifier_dev_class)


async def test_ha_status_received(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_ha_status_received(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(devices=1, codec=0)
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size(
            "devices"
        )  # 4 sensors per codec=0 device
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == get_size("devices")
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        # expecting config message per sensor + 1 bridge, 1 removal, 1 sensor data initialization message, 1 bridge state message
        configs = removals = status_online = up_msg = 0
        for msg in config_topics:
            sub_topics = msg[0].split("/")
            if sub_topics[-1] == "config":
                if msg[1] is not None:
                    configs += 1
                else:
                    removals += 1
            if sub_topics[-1] == "status":
                status_online += 1
            if sub_topics[-1] == "up":
                up_msg += 1
        assert len(config_topics) == configs + removals + status_online + up_msg
        assert configs == get_size("sensors") * get_size("devices") + BRIDGE_CONF_COUNT
        assert status_online == 1
        for i in range(
            0, mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices + 1
        ):  # +1 to ensure message for non-registered device
            dev_eui = f"dev_eui{i}"
            topic = f"application/{config.data.get(CONF_APPLICATION_ID)}/device/{dev_eui}/event/cur"
            msg = f'{{"time_stamp":{time.time()-200}}}'
            mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).on_message(mqtt.Client(mqtt.CallbackAPIVersion.VERSION2), None, message(topic, msg))
        await hass.async_block_till_done()
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        # check for topic count matching device count
        assert len(config_topics) == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices + 1
        for i in range(0, mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices):
            dev_eui = f"dev_eui{i}"
            topic = f"application/{config.data.get(CONF_APPLICATION_ID)}/device/{dev_eui}/event/up"
            msg = f'{{"batteryLevel": 93,"object": {{"{dev_eui}": 9}},"rxInfo": [{{"rssi": -75,"snr": 6,"location": {{"latitude": 56.9,"longitude": 24.1}}}}]}}'
            mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).on_message(mqtt.Client(mqtt.CallbackAPIVersion.VERSION2), None, message(topic, msg))
        await hass.async_block_till_done()
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        assert len(config_topics) == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices
        set_size(devices=0, codec=0)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("devices")

    await common.chirp_setup_and_run_test(hass, True, run_test_ha_status_received)


async def test_ha_status_received_with_debug_log(hass: HomeAssistant):
    """Test diagnostics log content for hat fw version starting from 1.6."""

    async def run_test_ha_status_received_with_debug_log(
        hass: HomeAssistant, config: ConfigEntry
    ):
        await hass.async_block_till_done()
        set_size(devices=1, codec=0)
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size(
            "devices"
        )  # 4 sensors per codec=0 device
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == 1
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        # expecting config message per sensor + 1 bridge, 1 removal, 1 sensor data initialization message, 1 bridge state message
        configs = removals = status_online = up_msg = 0
        for msg in config_topics:
            sub_topics = msg[0].split("/")
            if sub_topics[-1] == "config":
                if msg[1] is not None:
                    configs += 1
                else:
                    removals += 1
            if sub_topics[-1] == "status":
                status_online += 1
            if sub_topics[-1] == "up":
                up_msg += 1
        assert len(config_topics) == configs + removals + status_online + up_msg
        assert configs == get_size("sensors") * get_size("devices") + BRIDGE_CONF_COUNT
        assert status_online == 1
        for i in range(
            0, mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices + 1
        ):  # +1 to ensure message for non-registered device
            dev_eui = f"dev_eui{i}"
            topic = f"application/{config.data.get(CONF_APPLICATION_ID)}/device/{dev_eui}/event/cur"
            msg = f'{{"time_stamp":{time.time()-200}}}'
            mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).on_message(mqtt.Client(mqtt.CallbackAPIVersion.VERSION2), None, message(topic, msg))
        await hass.async_block_till_done()
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        # check for topic count matching device count
        assert len(config_topics) == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices + 1
        for i in range(0, mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices):
            dev_eui = f"dev_eui{i}"
            topic = f"application/{config.data.get(CONF_APPLICATION_ID)}/device/{dev_eui}/event/up"
            msg = f'{{"batteryLevel": 93,"object": {{"{dev_eui}": 9}},"rxInfo": [{{"rssi": -75,"snr": 6,"location": {{"latitude": 56.9,"longitude": 24.1}}}}]}}'
            mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).on_message(
                mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices, None, message(topic, msg)
            )
        await hass.async_block_till_done()
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        assert len(config_topics) == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices
        set_size(devices=0, codec=0)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0

    await common.chirp_setup_and_run_test(
        hass, True, run_test_ha_status_received_with_debug_log, True
    )


async def test_payload_join(hass: HomeAssistant):
    """Test payload join for array data with more than 1 sublevel."""

    async def run_test_payload_join(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(devices=1, codec=0)
        await common.reload_devices(hass, config)
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 4 * get_size(
            "devices"
        )  # 4 sensors per codec=0 device
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == 1
        for i in range(0, mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices):
            dev_eui = f"dev_eui{i}"
            topic = f"application/{config.data.get(CONF_APPLICATION_ID)}/device/{dev_eui}/event/cur"
            msg = f'{{"time_stamp":{time.time()-200},"rxInfo":[{{"location":{{"altitude":11}}}}]}}'
            mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).on_message(mqtt.Client(mqtt.CallbackAPIVersion.VERSION2), None, message(topic, msg))
        await hass.async_block_till_done()
        config_topics = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).get_published()
        assert len(config_topics) == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices

    await common.chirp_setup_and_run_test(hass, True, run_test_payload_join)
