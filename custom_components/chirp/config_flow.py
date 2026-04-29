"""The ChirpStack LoRaWAN Integration - base configuration."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant import core, data_entry_flow, exceptions
from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_POLL,
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
)
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
    DEFAULT_API_KEY,
    DEFAULT_API_PORT,
    DEFAULT_API_SERVER,
    DEFAULT_APPLICATION,
    DEFAULT_MQTT_CHIRPSTACK_PREFIX,
    DEFAULT_MQTT_DISC,
    DEFAULT_MQTT_PORT,
    DEFAULT_MQTT_PWD,
    DEFAULT_MQTT_SERVER,
    DEFAULT_MQTT_USER,
    DEFAULT_OPTIONS_DEBUG_PAYLOAD,
    DEFAULT_OPTIONS_RESTORE_AGE,
    DEFAULT_OPTIONS_START_DELAY,
    DEFAULT_TENANT,
    DOMAIN,
)
from .grpc import ChirpGrpc
from .mqtt import ChirpToHA

_LOGGER = logging.getLogger(__name__)


class ChirpConfigFlow(ConfigFlow, domain=DOMAIN):
    """ChirpStack LoRaWAN configuration flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL
    _grpc_channel: ChirpGrpc | None = None
    _tenants_list: dict[str, str] = {}
    _apps_list: dict[str, str] = {}
    _input: dict[str, Any] = {}
    _tenant_id: str | None = None
    _app_id: str | None = None
    _gateway_id: str | None = None

    def __init__(self) -> None:
        """Set initial values for ChirpConfigFlow."""
        self._config_defaults: dict[str, Any] = {
            CONF_API_SERVER: DEFAULT_API_SERVER,
            CONF_API_PORT: DEFAULT_API_PORT,
            CONF_API_KEY: DEFAULT_API_KEY,
            CONF_TENANT: DEFAULT_TENANT,
            CONF_APPLICATION: DEFAULT_APPLICATION,
            CONF_MQTT_SERVER: DEFAULT_MQTT_SERVER,
            CONF_MQTT_PORT: DEFAULT_MQTT_PORT,
            CONF_MQTT_USER: DEFAULT_MQTT_USER,
            CONF_MQTT_PWD: DEFAULT_MQTT_PWD,
            CONF_MQTT_DISC: DEFAULT_MQTT_DISC,
            CONF_MQTT_CHIRPSTACK_PREFIX: DEFAULT_MQTT_CHIRPSTACK_PREFIX,
        }
        _LOGGER.debug("ChirpConfigFlow.__init__")

    def __del__(self):
        """Close grpc channel on exit."""
        if self._grpc_channel:
            self._grpc_channel.close()
            self._grpc_channel = None
            _LOGGER.debug("__del__ causing grpc close")

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        config_entry: ConfigEntry[Any] = self._get_reconfigure_entry()
        self._config_defaults = config_entry.data.copy()
        return await self.async_step_user()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Run initial configuration step, check grpc api server access, proceed to tenant/application selection."""
        errors: dict[str, str] = {}
        if not self._grpc_channel and self.source == SOURCE_RECONFIGURE:
            self._grpc_channel = ChirpGrpc(self._config_defaults, None)
            self._gateway_id = self._grpc_channel.gateway_id
            self._tenants_list = self._grpc_channel.get_chirp_tenants()

        if user_input is not None:
            try:
                if self.source == SOURCE_USER:
                    user_input[CONF_APPLICATION_ID] = ""
                self._config_defaults = self._config_defaults | user_input
                if self._grpc_channel:
                    self._grpc_channel.close()
                self._grpc_channel = ChirpGrpc(self._config_defaults, None)
                self._gateway_id = self._grpc_channel.gateway_id
                self._tenants_list = self._grpc_channel.get_chirp_tenants()
                _LOGGER.debug("tenants_list %s", self._tenants_list)
                self._input = user_input
                return await self.async_step_select_tenant()
            except Exception as error:  # noqa: BLE001
                _LOGGER.error(
                    "Connection to ChirpStack API server (%s:%s, application key:%s) failed with %s",
                    user_input[CONF_API_SERVER],
                    user_input[CONF_API_PORT],
                    user_input[CONF_API_KEY],
                    str(error),
                )
                errors[CONF_API_SERVER] = CONF_ERROR_CHIRP_CONN_FAILED

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_SERVER,
                        default=self._config_defaults.get(
                            CONF_API_SERVER, vol.UNDEFINED
                        ),
                    ): vol.All(str, vol.Length(min=3)),
                    vol.Required(
                        CONF_API_PORT,
                        default=self._config_defaults.get(CONF_API_PORT, vol.UNDEFINED),
                    ): vol.All(int, vol.Range(min=0, max=0xFFFF)),
                    vol.Required(
                        CONF_API_KEY,
                        default=self._config_defaults.get(CONF_API_KEY, vol.UNDEFINED),
                    ): vol.All(str, vol.Length(min=10)),
                }
            ),
            errors=errors,
        )

    async def async_step_select_tenant(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select tenant, autoselect if only 1 exists."""
        errors: dict[str, str] = {}

        if len(self._tenants_list.keys()) == 1:
            user_input = {CONF_TENANT: list(self._tenants_list.keys())[0]}

        if user_input is not None:
            self._input |= user_input
            self._config_defaults = self._config_defaults | user_input
            selected_tenant = user_input.get(CONF_TENANT, "")
            self._tenant_id = self._tenants_list.get(selected_tenant)
            self._apps_list = (
                self._grpc_channel.get_tenant_applications(self._tenant_id)
                if self._grpc_channel
                else {}
            )
            return await self.async_step_select_application()

        return self.async_show_form(
            step_id="select_tenant",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TENANT,
                        default=self._config_defaults.get(CONF_TENANT, vol.UNDEFINED),
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

    async def async_step_select_application(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select application, autoselect if only 1 exists."""
        errors: dict[str, str] = {}

        if len(list(self._apps_list.keys())) == 1:
            user_input = {CONF_APPLICATION: list(self._apps_list.keys())[0]}

        if user_input is not None:
            self._input |= user_input
            self._config_defaults = self._config_defaults | user_input
            selected_app = user_input.get(CONF_APPLICATION, "")
            self._app_id = self._apps_list.get(selected_app)
            self._input[CONF_APPLICATION_ID] = self._app_id
            return await self.async_step_configure_mqtt()

        return self.async_show_form(
            step_id="select_application",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_APPLICATION,
                        default=self._config_defaults.get(
                            CONF_APPLICATION, vol.UNDEFINED
                        ),
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

    async def async_step_configure_mqtt(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure MQQT server and check connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._input |= user_input
            self._config_defaults = self._config_defaults | user_input

            try:
                await self.async_set_unique_id(self._gateway_id)
                try:
                    if self.source == SOURCE_USER:
                        self._abort_if_unique_id_configured()
                    if self.source == SOURCE_RECONFIGURE:
                        self._abort_if_unique_id_mismatch()
                except data_entry_flow.AbortFlow:
                    return self.async_abort(reason=CONF_CHIRP_SERVER_RESERVED)

                if self._grpc_channel:
                    ChirpToHA(
                        self._input,
                        None,
                        None,
                        self._grpc_channel,
                        connectivity_check_only=True,
                    ).close()
                if self.source == SOURCE_RECONFIGURE:
                    _LOGGER.info(
                        "ChirpConfigFlow.async_step_configure_mqtt finalizing reconfiguration"
                    )
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(),
                        data_updates=self._input
                        | self._get_reconfigure_entry().options,
                        options={
                            CONF_OPTIONS_START_DELAY: DEFAULT_OPTIONS_START_DELAY,
                            CONF_OPTIONS_RESTORE_AGE: DEFAULT_OPTIONS_RESTORE_AGE,
                            CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
                        },
                    )
                if self.source == SOURCE_USER:
                    _LOGGER.info(
                        "ChirpConfigFlow.async_step_configure_mqtt creating configuration entry"
                    )
                    return self.async_create_entry(
                        title=f"{self._gateway_id}",
                        data=self._input,
                        options={
                            CONF_OPTIONS_START_DELAY: DEFAULT_OPTIONS_START_DELAY,
                            CONF_OPTIONS_RESTORE_AGE: DEFAULT_OPTIONS_RESTORE_AGE,
                            CONF_OPTIONS_DEBUG_PAYLOAD: DEFAULT_OPTIONS_DEBUG_PAYLOAD,
                        },
                    )

            except Exception as error:  # noqa: BLE001
                _LOGGER.error(
                    "Connection to MQTT server (%s:%s) failed with %s",
                    user_input[CONF_MQTT_SERVER],
                    user_input[CONF_MQTT_PORT],
                    str(error),
                    # exc_info=1,
                )
                errors[CONF_MQTT_SERVER] = CONF_ERROR_MQTT_CONN_FAILED

        return self.async_show_form(
            step_id="configure_mqtt",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_MQTT_SERVER,
                        default=self._config_defaults.get(
                            CONF_MQTT_SERVER, vol.UNDEFINED
                        ),
                    ): vol.All(str, vol.Length(min=3)),
                    vol.Required(
                        CONF_MQTT_PORT,
                        default=self._config_defaults.get(
                            CONF_MQTT_PORT, vol.UNDEFINED
                        ),
                    ): vol.All(int, vol.Range(min=0, max=0xFFFF)),
                    vol.Required(
                        CONF_MQTT_USER,
                        default=self._config_defaults.get(
                            CONF_MQTT_USER, vol.UNDEFINED
                        ),
                    ): vol.All(str, vol.Length(min=1)),
                    vol.Required(
                        CONF_MQTT_PWD,
                        default=self._config_defaults.get(CONF_MQTT_PWD, vol.UNDEFINED)
                        if not user_input
                        else user_input[CONF_MQTT_PWD],
                    ): str,
                    vol.Required(
                        CONF_MQTT_DISC,
                        default=self._config_defaults.get(CONF_MQTT_DISC, vol.UNDEFINED)
                        if not user_input
                        else user_input[CONF_MQTT_DISC],
                    ): vol.All(str, vol.Length(min=1)),
                    vol.Optional(
                        CONF_MQTT_CHIRPSTACK_PREFIX,
                        default=self._config_defaults.get(
                            CONF_MQTT_CHIRPSTACK_PREFIX, vol.UNDEFINED
                        )
                        if not user_input
                        else user_input.get(
                            CONF_MQTT_CHIRPSTACK_PREFIX, DEFAULT_MQTT_CHIRPSTACK_PREFIX
                        ),
                    ): str,
                }
            ),
            errors=errors,
        )


class AlreadyConfigured(exceptions.HomeAssistantError):
    """Error to indicate device is already configured."""
