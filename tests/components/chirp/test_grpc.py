"""Test the Wan integration gRPC interface class."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from tests.components.chirp import common
import asyncio

from .patches import get_size, mqtt, set_size


async def test_faulty_codec(hass: HomeAssistant):
    """Test faulty codec - devices are not installed."""

    async def run_test_faulty_codec(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(devices=1, codec=3)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == 0 and mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0
#                    assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("idevices")
#                    assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == get_size("idevices")

    await common.chirp_setup_and_run_test(hass, True, run_test_faulty_codec)


async def test_codec_with_single_q_strings(hass: HomeAssistant):
    """Test codec with ' as string encloser - devices to be installed."""

    async def run_test_codec_with_single_q_strings(
        hass: HomeAssistant, config: ConfigEntry
    ):
        print("run_test_codec_with_single_q_strings 1")
        set_size(devices=1, codec=16)
        print("run_test_codec_with_single_q_strings 2")
        await common.reload_devices(hass, config)
        print("run_test_codec_with_single_q_strings 3")
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("idevices")

    await common.chirp_setup_and_run_test(
        hass, True, run_test_codec_with_single_q_strings
    )


async def test_with_devices_disabled(hass: HomeAssistant):
    """Test disabled devices are listed - no devices to be installed."""

    async def run_test_with_devices_disabled(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(disabled=True)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_with_devices_disabled)


async def test_codec_prologue_issues(hass: HomeAssistant):
    """Test codec with issues in prologue, no ddevices to be installed."""

    async def run_test_codec_prologue_issues(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(devices=1, codec=11)  # function name missing
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0
        set_size(devices=1, codec=12)  # return statement missing
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0
        set_size(devices=1, codec=13)  # { after return statement missing
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_codec_prologue_issues)


async def test_codec_with_comment(hass: HomeAssistant):
    """Test codec with comments in body."""

    async def run_test_codec_with_comment(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(codec=4)  # correct comment, codec correct
        await common.reload_devices(hass, config)
        await hass.async_block_till_done()
        assert get_size("idevices") == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices  ### device count check
        set_size(codec=14)  # incorrect comment, codec should fail
        await common.reload_devices(hass, config)
        await hass.async_block_till_done()
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_codec_with_comment)
