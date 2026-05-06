"""Test the ChirpStack LoRaWAN integration config (and config options) flow."""

import asyncio
import logging
from unittest import mock

from pychirpha.const import (
    CONF_API_KEY,
    CONF_API_PORT,
    CONF_API_SERVER,
    CONF_APPLICATION,
    CONF_APPLICATION_ID,
    CONF_CHIRP_SERVER_RESERVED,
    CONF_ERROR_CHIRP_CONN_FAILED,
    CONF_ERROR_MQTT_CONN_FAILED,
    CONF_MQTT_CHIRPSTACK_PREFIX,
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
)
import pytest

from homeassistant import config_entries, data_entry_flow
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from . import common
from .patches import api, grpc, mqtt, set_size

from tests.common import MockConfigEntry

_LOGGER = logging.getLogger(__name__)

# pytest ./tests/components/chirp/ --cov=pychirpha --cov-report term-missing -vv
# pytest ./tests/components/chirp/test_config_flow.py --cov=pychirpha --cov-report term-missing -vv


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


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_initialization_with_valid_configuration(hass: HomeAssistant) -> None:
    """Test if predefined/correct configuration is operational."""

    async def run_test_entry_options(hass: HomeAssistant, entry):
        return

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_options)


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_grpc_connection_failure(hass: HomeAssistant) -> None:
    """Test configuration with incorrect ChirpStack api server configuration."""
    set_size(grpc=0)  # connection to fail

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"]
    assert result["errors"][CONF_API_SERVER] == CONF_ERROR_CHIRP_CONN_FAILED


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_no_tenants(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with no tenants - expecting error message."""
    set_size(tenants=0)  # report no tenants

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_autoselected_tenant_no_apps(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with single tenant (autoselection) and no applications."""
    set_size(tenants=1, applications=0)  # report no tenants

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_tenant_selection_no_apps(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with several tenants and no applications."""
    set_size(applications=0)  # report no tenants

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "select_tenant"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_TENANT: "TenantName1",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_auto_tenant_auto_apps(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with auto tenant selection and single application (autoselection)."""
    set_size(tenants=1, applications=1)  # report no tenants
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "configure_mqtt"


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_auto_tenant_apps_selection(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with auto tenant and several applications."""
    set_size(tenants=1, applications=2, single_tenant=0)  # report no tenants

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "select_application"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_APPLICATION: "ApplicationName1",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {}
    assert result["step_id"] == "configure_mqtt"


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_auto_tenant_auto_apps_mqtt_fail(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with auto tenant and application selection, but with failing mqtt connection."""
    set_size(tenants=1, mqtt=0)  # report no tenants

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MQTT_SERVER: "localhost",
            CONF_MQTT_PORT: 1883,
            CONF_MQTT_USER: "user",
            CONF_MQTT_PWD: "pwd",
            CONF_MQTT_DISC: "ha",
            CONF_MQTT_CHIRPSTACK_PREFIX: "",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["errors"][CONF_MQTT_SERVER] == CONF_ERROR_MQTT_CONN_FAILED
    assert result["step_id"] == "configure_mqtt"


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_auto_tenant_auto_apps_mqtt(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with auto tenant and application selection, working mqtt connection."""
    set_size(tenants=1)  # report 1 tenant

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MQTT_SERVER: "localhost",
            CONF_MQTT_PORT: 1883,
            CONF_MQTT_USER: "user",
            CONF_MQTT_PWD: "pwd",
            CONF_MQTT_DISC: "ha",
            CONF_MQTT_CHIRPSTACK_PREFIX: "",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_API_SERVER: "localhost",
        CONF_API_PORT: 8080,
        CONF_API_KEY: common.DEF_API_KEY,
        CONF_TENANT: "TenantName0",
        CONF_APPLICATION: "ApplicationName0",
        CONF_APPLICATION_ID: "ApplicationId0",
        CONF_MQTT_SERVER: "localhost",
        CONF_MQTT_PORT: 1883,
        CONF_MQTT_USER: "user",
        CONF_MQTT_PWD: "pwd",
        CONF_MQTT_DISC: "ha",
        CONF_MQTT_CHIRPSTACK_PREFIX: "",
    }
    assert result["options"] == {
        CONF_OPTIONS_START_DELAY: DEFAULT_OPTIONS_START_DELAY,
        CONF_OPTIONS_RESTORE_AGE: DEFAULT_OPTIONS_RESTORE_AGE,
        CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
    }


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_tenant_apps_mqtt(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with tenant and application selections, working mqtt connection."""
    set_size(
        tenants=2, applications=2, single_tenant=0
    )  # report 2 tenants, 2 applications

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_tenant"
    assert result["errors"] == {}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_TENANT: "TenantName0",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_application"
    assert result["errors"] == {}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_APPLICATION: "ApplicationName0",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "configure_mqtt"
    assert result["errors"] == {}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MQTT_SERVER: "localhost",
            CONF_MQTT_PORT: 1883,
            CONF_MQTT_USER: "user",
            CONF_MQTT_PWD: "pwd",
            CONF_MQTT_DISC: "ha",
            CONF_MQTT_CHIRPSTACK_PREFIX: "",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_API_SERVER: "localhost",
        CONF_API_PORT: 8080,
        CONF_API_KEY: common.DEF_API_KEY,
        CONF_TENANT: "TenantName0",
        CONF_APPLICATION: "ApplicationName0",
        CONF_APPLICATION_ID: "ApplicationId0",
        CONF_MQTT_SERVER: "localhost",
        CONF_MQTT_PORT: 1883,
        CONF_MQTT_USER: "user",
        CONF_MQTT_PWD: "pwd",
        CONF_MQTT_DISC: "ha",
        CONF_MQTT_CHIRPSTACK_PREFIX: "",
    }
    assert result["options"] == {
        CONF_OPTIONS_START_DELAY: DEFAULT_OPTIONS_START_DELAY,
        CONF_OPTIONS_RESTORE_AGE: DEFAULT_OPTIONS_RESTORE_AGE,
        CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
    }


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_setup_with_duplicate(hass: HomeAssistant) -> None:
    """Test for configuration abort in case hat already in use."""
    set_size(tenants=1)  # report no tenants

    conf_data = {
        CONF_API_SERVER: "localhost",
        CONF_API_PORT: 8080,
        CONF_API_KEY: common.DEF_API_KEY,
        CONF_TENANT: "TenantName0",
        CONF_APPLICATION: "ApplicationName0",
        CONF_APPLICATION_ID: "ApplicationId0",
        CONF_MQTT_SERVER: "localhost",
        CONF_MQTT_PORT: 1883,
        CONF_MQTT_USER: "user",
        CONF_MQTT_PWD: "pwd",
        CONF_MQTT_DISC: "ha",
        CONF_MQTT_CHIRPSTACK_PREFIX: "",
    }
    conf_options = {
        CONF_OPTIONS_START_DELAY: DEFAULT_OPTIONS_START_DELAY,
        CONF_OPTIONS_RESTORE_AGE: DEFAULT_OPTIONS_RESTORE_AGE,
        CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
    }
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="gatewayId0",
        data=conf_data,
        options=conf_options,
    )

    # Load config_entry.
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: "localhost",
            CONF_API_PORT: 8080,
            CONF_API_KEY: common.DEF_API_KEY,
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MQTT_SERVER: "localhost",
            CONF_MQTT_PORT: 1883,
            CONF_MQTT_USER: "user",
            CONF_MQTT_PWD: "pwd",
            CONF_MQTT_DISC: "ha",
            CONF_MQTT_CHIRPSTACK_PREFIX: "",
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == CONF_CHIRP_SERVER_RESERVED


@mock.patch("pychirpha.grpc.api", new=api)
@mock.patch("pychirpha.grpc.grpc", new=grpc)
@mock.patch("pychirpha.mqtt.mqtt", new=mqtt)
async def test_reconfiguration(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Test reconfiguration."""
    caplog.set_level(5)
    config_entry = await common.chirp_get_working_configuration(hass)
    nonconfigurables =  [CONF_OPTIONS_DEBUG_PAYLOAD,
                         CONF_OPTIONS_RESTORE_AGE,
                         CONF_OPTIONS_START_DELAY,
                        ]
    orig_conf = config_entry.data
    reconf_conf = orig_conf.copy()
    for conf_key in reconf_conf:
        if  conf_key not in nonconfigurables:
            if conf_key == CONF_TENANT:
                reconf_conf[conf_key] = "TenantName1"
            elif  conf_key == CONF_APPLICATION:
                reconf_conf[conf_key] = "ApplicationName1"
            elif  conf_key == CONF_APPLICATION_ID:
                _LOGGER.info("Updates for key %s %s", conf_key, reconf_conf[conf_key])
                reconf_conf[conf_key] = "ApplicationId1"
                _LOGGER.info("Updates for key %s %s", conf_key, reconf_conf[conf_key])
            elif type(reconf_conf[conf_key]) is int:
                reconf_conf[conf_key] += 1
            elif type(reconf_conf[conf_key]) is str:
                reconf_conf[conf_key] += "X"
        _LOGGER.info("Updates %s %s", conf_key, reconf_conf[conf_key])
    assert orig_conf != reconf_conf
    _LOGGER.info("Original configuration loaded")
    _LOGGER.info("Updated vonfiguration %s", orig_conf)
    _LOGGER.info("Updated vonfiguration %s", reconf_conf)
    await asyncio.sleep(1)
    caplog.set_level(5)

    set_size(single_tenant=1, applications=3)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": config_entry.entry_id,
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}
    _LOGGER.detail("Configuration flow @ %s", result["step_id"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_API_SERVER: reconf_conf[CONF_API_SERVER],
            CONF_API_PORT: reconf_conf[CONF_API_PORT],
            CONF_API_KEY: reconf_conf[CONF_API_KEY],
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_tenant"
    assert result["errors"] == {}
    _LOGGER.detail("Configuration flow @ %s", result["step_id"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_TENANT: reconf_conf[CONF_TENANT],
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "select_application"
    assert result["errors"] == {}
    _LOGGER.detail("Configuration flow @ %s", result["step_id"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_APPLICATION: reconf_conf[CONF_APPLICATION],
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM
    assert result["step_id"] == "configure_mqtt"
    assert result["errors"] == {}
    _LOGGER.detail("Configuration flow @ %s", result["step_id"])

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_MQTT_SERVER: reconf_conf[CONF_MQTT_SERVER],
            CONF_MQTT_PORT: reconf_conf[CONF_MQTT_PORT],
            CONF_MQTT_USER: reconf_conf[CONF_MQTT_USER],
            CONF_MQTT_PWD: reconf_conf[CONF_MQTT_PWD],
            CONF_MQTT_DISC: reconf_conf[CONF_MQTT_DISC],
            CONF_MQTT_CHIRPSTACK_PREFIX: reconf_conf[CONF_MQTT_CHIRPSTACK_PREFIX],
        },
    )
    assert result["type"] == data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    mqtt.Client(mqtt.CallbackAPIVersion.VERSION2).wait_empty_queue()
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    for ck in reconf_conf:
        if ck not in nonconfigurables:
            assert reconf_conf[ck] == config_entry.data[ck]

    await hass.config_entries.async_reload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(config_entry.entry_id)
