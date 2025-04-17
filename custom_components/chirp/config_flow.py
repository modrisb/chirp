"""The ChirpStack LoRaWan integration - base configuration."""
import hashlib
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, core, data_entry_flow, exceptions
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
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
    CONF_OPTIONS_DEBUG_PAYLOAD,
    CONF_OPTIONS_RESTORE_AGE,
    CONF_OPTIONS_START_DELAY,
    CONF_TENANT,
    DEFAULT_API_KEY,
    DEFAULT_API_PORT,
    DEFAULT_API_SERVER,
    DEFAULT_APPLICATION,
    DEFAULT_MQTT_DISC,
    DEFAULT_MQTT_PORT,
    DEFAULT_MQTT_PWD,
    DEFAULT_MQTT_SERVER,
    DEFAULT_MQTT_USER,
    DEFAULT_NAME,
    DEFAULT_OPTIONS_DEBUG_PAYLOAD,
    DEFAULT_OPTIONS_RESTORE_AGE,
    DEFAULT_OPTIONS_START_DELAY,
    DEFAULT_TENANT,
    DOMAIN,
)
from .grpc import ChirpGrpc
from .mqtt import ChirpToHA

_LOGGER = logging.getLogger(__name__)


def generate_unique_id(configuration):
    """Create untegration unique id based on api/mqtt servers configurations."""
    u_id = "".join(
        [
            str(configuration[id_key])
            for id_key in (
                CONF_API_SERVER,
                CONF_API_PORT,
                CONF_TENANT,
                CONF_APPLICATION,
                CONF_MQTT_SERVER,
                CONF_MQTT_PORT,
                CONF_MQTT_DISC,
            )
        ]
    )
    unique_id = f"{hashlib.md5(u_id.encode('utf-8')).hexdigest()}"
    return unique_id


class ChirpConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Chirpstack LoRaWan configuration flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL
    _grpc_channel = None
    _tenants_list = None
    _apps_list = None
    _input = None
    _tenant_id = None
    _app_id = None

    def __init__(self) -> None:
        """Set initial values for ChirpConfigFlow."""
        self._hass: core.HomeAssistant = core.async_get_hass()
        _LOGGER.debug("ChirpConfigFlow.__init__")

    def __del__(self):
        """Close grpc channel on exit."""
        if self._grpc_channel:
            self._grpc_channel.close()

    async def async_step_user(self, user_input: dict[str, Any] = None) -> FlowResult:
        """Run initial configuration step, check grpc api server access, proceed to tenant/application selection."""
        errors = {}

        if user_input is not None:
            try:
                user_input[CONF_APPLICATION_ID] = ""
                self._grpc_channel = ChirpGrpc(user_input, None)
                self._tenants_list = self._grpc_channel.get_chirp_tenants()
                if self._tenants_list == {}:
                    errors[CONF_API_SERVER] = CONF_CHIRP_NO_TENANTS
                else:
                    self._input = user_input
                    return await self.async_step_select_tenant()
            except Exception as error:  # pylint: disable=broad-exception-caught
                _LOGGER.error(
                    "Connection to ChirpStack API server (%s:%s, application key:%s) failed with %s",
                    user_input[CONF_API_SERVER],
                    user_input[CONF_API_PORT],
                    user_input[CONF_API_KEY],
                    str(error),
                    exc_info=1,
                )
                errors[CONF_API_SERVER] = CONF_ERROR_CHIRP_CONN_FAILED

        chirp_configuration = self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_SERVER,
                        default=DEFAULT_API_SERVER
                        if not user_input
                        else user_input[CONF_API_SERVER],
                    ): vol.All(str,vol.Length(min=3)),
                    vol.Required(
                        CONF_API_PORT,
                        default=DEFAULT_API_PORT
                        if not user_input
                        else user_input[CONF_API_PORT],
                    ): vol.All(int, vol.Range(min=0,max=0xffff)),
                    vol.Required(
                        CONF_API_KEY,
                        default=DEFAULT_API_KEY
                        if not user_input
                        else user_input[CONF_API_KEY],
                    ): vol.All(str,vol.Length(min=10)),
                }
            ),
            errors=errors,
        )
        return chirp_configuration

    async def async_step_select_tenant(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Select tenant, autoselect if only 1 exists."""
        errors = {}

        if len(list(self._tenants_list.keys())) == 1:
            user_input = {CONF_TENANT: list(self._tenants_list.keys())[0]}

        if user_input is not None:
            self._input |= user_input
            selected_tenant = user_input[CONF_TENANT]
            self._tenant_id = self._tenants_list[selected_tenant]
            self._apps_list = self._grpc_channel.get_tenant_applications(
                self._tenant_id
            )
            if self._apps_list == {}:
                errors[CONF_API_SERVER] = CONF_ERROR_NO_APPS
            else:
                return await self.async_step_select_application()

        chirp_configuration = self.async_show_form(
            step_id="select_tenant",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TENANT,
                        default=DEFAULT_TENANT,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(self._tenants_list.keys()),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )
        return chirp_configuration

    async def async_step_select_application(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Select application, autoselect if only 1 exists."""
        errors = {}

        if len(list(self._apps_list.keys())) == 1:
            user_input = {CONF_APPLICATION: list(self._apps_list.keys())[0]}

        if user_input is not None:
            self._input |= user_input
            selected_app = user_input[CONF_APPLICATION]
            self._app_id = self._apps_list[selected_app]
            self._input[CONF_APPLICATION_ID] = self._app_id
            return await self.async_step_configure_mqtt()

        chirp_configuration = self.async_show_form(
            step_id="select_application",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_APPLICATION, default=DEFAULT_APPLICATION): str,
                    vol.Required(
                        CONF_APPLICATION,
                        default=DEFAULT_APPLICATION,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(self._apps_list.keys()),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )
        return chirp_configuration

    async def async_step_configure_mqtt(
        self, user_input: dict[str, Any] = None
    ) -> FlowResult:
        """Configure MQQT server and check connection."""
        errors = {}

        if user_input is not None:
            self._input |= user_input

            try:
                unique_id = generate_unique_id(self._input)
                await self.async_set_unique_id(unique_id)
                try:
                    self._abort_if_unique_id_configured()
                except data_entry_flow.AbortFlow:
                    return self.async_abort(reason=CONF_CHIRP_SERVER_RESERVED)

                entry = lambda: None
                entry.data = self._input
                entry.options = {}
                entry.unique_id = unique_id
                mqtt_client = ChirpToHA(entry.data, None, None, self._grpc_channel)
                mqtt_client.close()
                return self.async_create_entry(
                    title=DEFAULT_NAME,
                    data=self._input,
                    options={
                        CONF_OPTIONS_START_DELAY: DEFAULT_OPTIONS_START_DELAY,
                        CONF_OPTIONS_RESTORE_AGE: DEFAULT_OPTIONS_RESTORE_AGE,
                        CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
                    },
                )

            except Exception as error:  # pylint: disable=broad-exception-caught
                _LOGGER.error(
                    "Connection to MQTT server (%s:%s) failed with %s",
                    user_input[CONF_MQTT_SERVER],
                    user_input[CONF_MQTT_PORT],
                    str(error),
                    exc_info=1,
                )
                errors[CONF_MQTT_SERVER] = CONF_ERROR_MQTT_CONN_FAILED

        chirp_configuration = self.async_show_form(
            step_id="configure_mqtt",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MQTT_SERVER,
                        default=DEFAULT_MQTT_SERVER
                        if not user_input
                        else user_input[CONF_MQTT_SERVER],
                    ): vol.All(str,vol.Length(min=3)),
                    vol.Required(
                        CONF_MQTT_PORT,
                        default=DEFAULT_MQTT_PORT
                        if not user_input
                        else user_input[CONF_MQTT_PORT],
                    ): vol.All(int, vol.Range(min=0,max=0xffff)),
                    vol.Required(
                        CONF_MQTT_USER,
                        default=DEFAULT_MQTT_USER
                        if not user_input
                        else user_input[CONF_MQTT_USER],
                    ): vol.All(str,vol.Length(min=1)),
                    vol.Required(
                        CONF_MQTT_PWD,
                        default=DEFAULT_MQTT_PWD
                        if not user_input
                        else user_input[CONF_MQTT_PWD],
                    ): str,
                    vol.Required(
                        CONF_MQTT_DISC,
                        default=DEFAULT_MQTT_DISC
                        if not user_input
                        else user_input[CONF_MQTT_DISC],
                    ): vol.All(str,vol.Length(min=1)),
                }
            ),
            errors=errors,
        )
        return chirp_configuration


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate device is already configured."""
