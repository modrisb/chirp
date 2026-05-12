"""The ChirpStack LoRaWAN Integration - constant definitions."""
from homeassistant.helpers.device_registry import DeviceInfo

DOMAIN = "chirp"
GRPCLIENT = "grpclient"
MQTTCLIENT = "mqttclient"

CONF_CHIRP_SERVER_RESERVED = "chirp_server_reserved"
CONF_ERROR_CHIRP_CONN_FAILED = "chirpstack_connection_failed"
CONF_ERROR_MQTT_CONN_FAILED = "mqtt_connection_failed"

STATISTICS_SENSORS = "chirp_sensors"
STATISTICS_DEVICES = "chirp_devices"
STATISTICS_UPDATED = "chirp_updated"
RELOAD_BUTTON = "chirp_reload"

DEVICE_INFO: list[DeviceInfo] = []
INTEGRATION_DEV_NAME = "adi"
INTEGRATION_DEV_TRANSLATION_KEY = "auto_discovery_device"
