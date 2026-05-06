"""Test the Wan integration gRPC interface class."""

import pytest

from homeassistant.config_entries import ConfigEntry
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


async def test_faulty_codec(hass: HomeAssistant) -> None:
    """Test faulty codec - devices are not installed."""

    async def run_test_faulty_codec(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(devices=1, codec=3)
        await common.reload_devices(hass, config)
        assert (
            mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == 0
            and mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0
        )

    #                    assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size("sensors") * get_size("idevices")
    #                    assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices == get_size("idevices")

    await common.chirp_setup_and_run_test(hass, True, run_test_faulty_codec)


async def test_codec_with_single_q_strings(hass: HomeAssistant) -> None:
    """Test codec with ' as string encloser - devices to be installed."""

    async def run_test_codec_with_single_q_strings(
        hass: HomeAssistant, config: ConfigEntry
    ):
        set_size(devices=1, codec=16)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == get_size(
            "sensors"
        ) * get_size("idevices")

    await common.chirp_setup_and_run_test(
        hass, True, run_test_codec_with_single_q_strings
    )


async def test_with_devices_disabled(hass: HomeAssistant) -> None:
    """Test disabled devices are listed - no devices to be installed."""

    async def run_test_with_devices_disabled(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(disabled=True)
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_with_devices_disabled)


async def test_codec_prologue_issues(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test codec with issues in prologue, no ddevices to be installed."""

    async def run_test_codec_prologue_issues(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(devices=1, codec=11)  # wrong function name (missing)
        await common.reload_devices(hass, config)
        assert (
            "discovery codec script not found, generating one, will use manufacturer name"
            in caplog.text
        )
        assert (
            mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 2
        )  # sensor count in generated codec is 2
        set_size(devices=1, codec=12)  # return statement missing
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0
        assert "discovery codec script error" in caplog.text
        set_size(devices=1, codec=13)  # { after return statement missing
        await common.reload_devices(hass, config)
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0
        assert "discovery codec script error" in caplog.text

    await common.chirp_setup_and_run_test(hass, True, run_test_codec_prologue_issues)


async def test_codec_with_comment(hass: HomeAssistant) -> None:
    """Test codec with comments in body."""

    async def run_test_codec_with_comment(hass: HomeAssistant, config: ConfigEntry):
        await hass.async_block_till_done()
        set_size(codec=4)  # correct comment, codec correct
        await common.reload_devices(hass, config)
        await hass.async_block_till_done()
        assert (
            get_size("idevices")
            == mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_devices
        )  ### device count check
        set_size(codec=14)  # incorrect comment, codec should fail
        await common.reload_devices(hass, config)
        await hass.async_block_till_done()
        assert mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).stat_sensors == 0

    await common.chirp_setup_and_run_test(hass, True, run_test_codec_with_comment)
