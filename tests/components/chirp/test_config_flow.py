"""Test the ChirpStack LoRaWAN integration config (and config options) flow."""
from unittest import mock

from homeassistant import config_entries, data_entry_flow
from homeassistant.components.chirp.config_flow import generate_unique_id
from homeassistant.components.chirp.const import (
    CONF_API_KEY,
    CONF_API_PORT,
    CONF_API_SERVER,
    CONF_APPLICATION,
    CONF_APPLICATION_ID,
    CONF_CHIRP_NO_TENANTS,
    CONF_CHIRP_SERVER_RESERVED,
    CONF_ERROR_CHIRP_CONN_FAILED,
    CONF_ERROR_MQTT_CONN_FAILED,
    CONF_ERROR_NO_APPS,
    CONF_MQTT_DISC,
    CONF_MQTT_PORT,
    CONF_MQTT_PWD,
    CONF_MQTT_SERVER,
    CONF_MQTT_USER,
    CONF_MQTT_CHIRPSTACK_PREFIX,
    CONF_OPTIONS_DEBUG_PAYLOAD,
    CONF_OPTIONS_RESTORE_AGE,
    CONF_OPTIONS_START_DELAY,
    CONF_TENANT,
    DEFAULT_OPTIONS_DEBUG_PAYLOAD,
    DEFAULT_OPTIONS_RESTORE_AGE,
    DEFAULT_OPTIONS_START_DELAY,
    DOMAIN,
)
from homeassistant.core import HomeAssistant
from tests.common import MockConfigEntry
from tests.components.chirp import common

from .patches import api, grpc, mqtt, set_size

# pytest ./tests/components/chirp/ --cov=homeassistant.components.chirp --cov-report term-missing -vv
# pytest ./tests/components/chirp/test_config_flow.py --cov=homeassistant.components.chirp --cov-report term-missing -vv


#@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
#@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
#@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
async def test_initialization_with_valid_configuration(hass: HomeAssistant) -> None:
    """Test if predefined/correct configuration is operational."""

    async def run_test_entry_options(hass: HomeAssistant, entry):
        return

    await common.chirp_setup_and_run_test(hass, True, run_test_entry_options)


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
async def test_setup_with_auto_tenant_apps_selection(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with auto tenant and several applications."""
    set_size(tenants=1, applications=2)  # report no tenants

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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
async def test_setup_with_auto_tenant_auto_apps_mqtt(hass: HomeAssistant) -> None:
    """Test connection to ChirpStack server with auto tenant and application selection, working mqtt connection."""
    set_size(tenants=1)  # report no tenants

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


@mock.patch("homeassistant.components.chirp.grpc.api", new=api)
@mock.patch("homeassistant.components.chirp.grpc.grpc", new=grpc)
@mock.patch("homeassistant.components.chirp.mqtt.mqtt", new=mqtt)
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
    unique_id = generate_unique_id(conf_data)
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=unique_id,
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
