"""The Chirpstack LoRaWan integration - constant definitions."""
DOMAIN = "chirp"
GRPCLIENT = "grpclient"
MQTTCLIENT = "mqttclient"
DEFAULT_NAME = "Chirp"

CONF_API_SERVER = "chirpstack_api_server"
CONF_API_PORT = "server_port"
CONF_API_KEY = "api_connection_key"
CONF_TENANT = "tenant"
CONF_APPLICATION = "application_name"
CONF_APPLICATION_ID = "application_id"

DEFAULT_API_SERVER = ""
DEFAULT_API_PORT = 8080
DEFAULT_API_KEY = ""
DEFAULT_TENANT = "ChirpStack"
DEFAULT_APPLICATION = "temp"

CONF_CHIRP_SERVER_RESERVED = "chirp_server_reserved"
CONF_CHIRP_NO_TENANTS = "chirp_server_no_tenants"
CONF_ERROR_NO_APPS = "tenant_no_applications"
CONF_ERROR_CHIRP_CONN_FAILED = "chirpstack_connection_failed"
CONF_ERROR_MQTT_CONN_FAILED = "mqtt_connection_failed"

CONF_MQTT_SERVER = "mqtt_server"
CONF_MQTT_PORT = "mqtt_port"
CONF_MQTT_USER = "mqtt_user"
CONF_MQTT_PWD = "mqtt_password"
CONF_MQTT_DISC = "discovery_prefix"

DEFAULT_MQTT_SERVER = "localhost"
DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTT_USER = ""
DEFAULT_MQTT_PWD = ""
DEFAULT_MQTT_DISC = "homeassistant"

CONF_OPTIONS_START_DELAY = "options_start_delay"
DEFAULT_OPTIONS_START_DELAY = 2
CONF_OPTIONS_RESTORE_AGE = "options_restore_age"
DEFAULT_OPTIONS_RESTORE_AGE = 4
CONF_OPTIONS_DEBUG_PAYLOAD = "options_debug_print_payload"
DEFAULT_OPTIONS_DEBUG_PAYLOAD = False

MQTT_ORIGIN = "ChirpLora"
BRIDGE_VENDOR = "Chirp2MQTT"
BRIDGE_NAME = "Chirp2MQTT Bridge"
BRIDGE = "Bridge"
BRIDGE_STATE_ID = "state"
BRIDGE_ENTITY_NAME = "Connection state"
INTEGRATION_DEV_NAME = "ChirpStack LoraWan Integration"
CONNECTIVITY_DEVICE_CLASS = "connectivity"
BRIDGE_RESTART_ID = "restart"
BRIDGE_RESTART_NAME = "Reload devices"

BRIDGE_CONF_COUNT = 2

STATISTICS_SENSORS = "chirp_sensors"
STATISTICS_DEVICES = "chirp_devices"
STATISTICS_UPDATED = "chirp_updated"
