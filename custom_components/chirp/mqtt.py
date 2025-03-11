"""The Chirpstack LoRaWan integration - mqtt interface."""
from __future__ import annotations

import datetime
import json
import logging
import re
import time
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.humidifier import (
    HumidifierDeviceClass,  # integration humidifier
)
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .const import (
    BRIDGE,
    BRIDGE_ENTITY_NAME,
    BRIDGE_NAME,
    BRIDGE_RESTART_ID,
    BRIDGE_RESTART_NAME,
    BRIDGE_STATE_ID,
    BRIDGE_VENDOR,
    CONF_APPLICATION_ID,
    CONF_MQTT_DISC,
    CONF_MQTT_PORT,
    CONF_MQTT_PWD,
    CONF_MQTT_SERVER,
    CONF_MQTT_USER,
    CONF_OPTIONS_DEBUG_PAYLOAD,
    CONF_OPTIONS_RESTORE_AGE,
    CONF_OPTIONS_START_DELAY,
    CONNECTIVITY_DEVICE_CLASS,
    DOMAIN,
    STATISTICS_DEVICES,
    STATISTICS_SENSORS,
    STATISTICS_UPDATED,
)
from .grpc import ChirpGrpc

_LOGGER = logging.getLogger(__name__)

UTC_TIMEZONE = ZoneInfo("UTC")


def to_lower_case_no_blanks(e_name):
    """Change string to lower case and replace blanks with _ ."""
    return e_name.lower().replace(" ", "_")


class ChirpToHA:
    """Chirpstack LoRaWan MQTT interface."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, grpc_client: ChirpGrpc
    ) -> None:
        """Open connection to HA MQTT server and initialize internal variables."""
        self._hass: HomeAssistant = hass
        self._entry: ConfigEntry = entry
        self._application_id = entry.data.get(CONF_APPLICATION_ID)
        self._grpc_client: ChirpGrpc = grpc_client
        self._host = self._entry.data.get(CONF_MQTT_SERVER)
        self._port = self._entry.data.get(CONF_MQTT_PORT)
        self._user = self._entry.data.get(CONF_MQTT_USER)
        self._pwd = self._entry.data.get(CONF_MQTT_PWD)
        self._dev_sensor_count = 0
        self._dev_count = 0
        self._last_update = None
        self._discovery_prefix = self._entry.data.get(CONF_MQTT_DISC)
        self._client = mqtt.Client()
        self._client.username_pw_set(self._user, self._pwd)
        self._client.connect(self._host, self._port)
        self._origin = {
            "name": BRIDGE_VENDOR,
            "sw_version": str(self._hass.data["integrations"][DOMAIN].version),
        }
        self._bridge_indentifier = to_lower_case_no_blanks(
            f"{BRIDGE_VENDOR} {BRIDGE} {self._entry.unique_id}"
        )
        self._bridge_init_time = None
        self._cur_open_time = None
        self._discovery_delay = self._entry.options.get(CONF_OPTIONS_START_DELAY)
        self._cur_age = self._entry.options.get(CONF_OPTIONS_RESTORE_AGE)
        self._devices_config_topics = set()
        self._old_devices_config_topics = set()
        self._messages_to_restore_values = []
        self._top_level_msg_names = None
        self._values_cache = {}
        self._config_topics_published = 0
        self._bridge_state_topic = f"application/{self._application_id}/bridge/status"
        self._bridge_restart_topic = (
            f"application/{self._application_id}/bridge/restart"
        )
        self._availability_element = None
        self._ha_status = f"{self._discovery_prefix}/status"
        self._sub_cur_topic = f"application/{self._application_id}/device/+/event/cur"
        self._finalize_connection = True
        self._print_payload = self._entry.options.get(CONF_OPTIONS_DEBUG_PAYLOAD)

    def start_bridge(self):
        """Start Lora bridge registration within HA MQTT."""
        bridge_publish_data = self.get_conf_data(
            BRIDGE_STATE_ID,
            {  #   'entities':
                "entity_conf": {
                    "state_topic": self._bridge_state_topic,
                    "value_template": "{{ value_json.state }}",
                    "object_id": to_lower_case_no_blanks(
                        f"{BRIDGE_VENDOR} {BRIDGE} {BRIDGE_ENTITY_NAME}"
                    ),
                    "unique_id": to_lower_case_no_blanks(
                        f"{BRIDGE} {self._entry.unique_id} {BRIDGE_ENTITY_NAME} {BRIDGE_VENDOR}"
                    ),
                    "device_class": CONNECTIVITY_DEVICE_CLASS,
                    "entity_category": str(EntityCategory.DIAGNOSTIC),
                    "payload_on": "online",
                    "payload_off": "offline",
                },
            },
            {  #   'device':
                "manufacturer": BRIDGE_VENDOR,
                "model": BRIDGE,
                "identifiers": [to_lower_case_no_blanks(self._bridge_indentifier)],
            },
            {  #   'dev_conf':
                "measurement_names": {BRIDGE_STATE_ID: BRIDGE_ENTITY_NAME},
                "dev_name": BRIDGE_NAME,
                "dev_eui": self._entry.unique_id,
            },
        )
        ret_val = self._client.publish(
            bridge_publish_data["discovery_topic"],
            bridge_publish_data["discovery_config"],
            retain=True,
        )
        _LOGGER.debug(
            "Bridge device configuration published. MQTT topic %s, publish code %s",
            bridge_publish_data["discovery_topic"],
            ret_val,
        )
        if self._print_payload:
            _LOGGER.debug(
                "Bridge device configuration published. MQTT payload %s",
                bridge_publish_data["discovery_config"],
            )

        bridge_refresh_data = self.get_conf_data(
            BRIDGE_RESTART_ID,
            {  #   'entities':
                "integration": "button",
                "entity_conf": {
                    "availability_mode": "all",
                    "state_topic": "{None}",
                    "command_topic": self._bridge_restart_topic,
                    "object_id": to_lower_case_no_blanks(
                        f"{BRIDGE_VENDOR} {BRIDGE} {BRIDGE_RESTART_ID}"
                    ),
                    "unique_id": to_lower_case_no_blanks(
                        f"{BRIDGE} {self._entry.unique_id} {BRIDGE_RESTART_NAME} {BRIDGE_VENDOR}"
                    ),
                    "device_class": "restart",
                    "payload_press": "",
                },
            },
            {  #   'device':
                "manufacturer": BRIDGE_VENDOR,
                "model": BRIDGE,
                "identifiers": [to_lower_case_no_blanks(self._bridge_indentifier)],
            },
            {  #   'dev_conf':
                "measurement_names": {BRIDGE_RESTART_ID: BRIDGE_RESTART_NAME},
                "dev_name": BRIDGE_NAME,
                "dev_eui": self._entry.unique_id,
            },
        )
        ret_val = self._client.publish(
            bridge_refresh_data["discovery_topic"],
            bridge_refresh_data["discovery_config"],
            retain=False,
        )

        self._availability_element = [
            {
                "topic": self._bridge_state_topic,
                "value_template": "{{ value_json.state }}",
            }
        ]

        device_sensors = self._grpc_client.get_current_device_entities()

        self._dev_sensor_count = 0
        self._dev_count = 0

        if self._finalize_connection:
            self._finalize_connection = False
            self._client.on_message = self.on_message
            # self._client.on_publish = self.on_publish_gen
            self._client.loop_start()

            self._bridge_init_time = time.time()
            self._client.subscribe(self._bridge_state_topic)
            self._client.subscribe(self._bridge_restart_topic)
            self._client.subscribe(self._ha_status)
            self._client.subscribe(
                f"application/{self._application_id}/device/+/event/up"
            )
            self._client.subscribe(f"{self._discovery_prefix}/+/+/+/config")

        self._devices_config_topics = set()
        devices_config_topics = set()
        self._config_topics_published = 0
        self._values_cache = {}
        self._messages_to_restore_values = []
        value_templates = []

        for device in device_sensors:
            previous_values = device["dev_conf"].get("prev_value")
            dev_eui = device["dev_conf"]["dev_eui"]
            self._values_cache[dev_eui] = {}
            for sensor in device["entities"]:
                sensor_entity_conf_data = self.get_conf_data(
                    sensor,
                    device["entities"][sensor],
                    device["device"],
                    device["dev_conf"],
                )
                value_templates.append(
                    sensor_entity_conf_data["discovery_config_struct"]["value_template"]
                )
                devices_config_topics.add(sensor_entity_conf_data["discovery_topic"])
                ret_val = self._client.publish(
                    sensor_entity_conf_data["discovery_topic"],
                    sensor_entity_conf_data["discovery_config"],
                    retain=True,
                )
                _LOGGER.info(
                    "Device sensor discovery message published. MQTT topic %s, publish code %s",
                    sensor_entity_conf_data["discovery_topic"],
                    ret_val,
                )
                if self._print_payload:
                    _LOGGER.debug(
                        "Device sensor published. MQTT payload %s",
                        sensor_entity_conf_data["discovery_config"],
                    )
                for sens_id in previous_values:
                    if (
                        sens_id
                        in device["entities"][sensor]["entity_conf"]["value_template"]
                    ):
                        topic_for_value = sensor_entity_conf_data["status_topic"]
                        payload_for_value = f'{{"{sens_id}":{str(previous_values[sens_id])},"time_stamp":{time.time()}}}'
                        self._messages_to_restore_values.append(
                            (topic_for_value, payload_for_value)
                        )
                self._dev_sensor_count += 1
            self._dev_count += 1

        self._devices_config_topics = devices_config_topics

        self._top_level_msg_names = {}
        for value_template in value_templates:
            for msg_name in re.findall(r"(value_json\..{1,}?)\ ", value_template):
                names = re.split(r"\.", msg_name[11:])
                level = self._top_level_msg_names
                for name in names:
                    name_t = re.split(r"\[", name)
                    if len(name_t) == 1:
                        if name not in level:
                            level[name] = {}
                        level = level[name]
                    else:
                        if name_t[0] not in level:
                            level[name_t[0]] = [{}]
                        level = level[name_t[0]][0]
        _LOGGER.debug("Top level names %s", self._top_level_msg_names)

        _LOGGER.info(
            "%s value restore requests queued", len(self._messages_to_restore_values)
        )
        _LOGGER.info(
            "Bridge (re)start completed, %s devices and %s sensors found",
            self._dev_count,
            self._dev_sensor_count,
        )

    def clean_up_disappeared(self):
        """Remove retained config messages from mqtt server if not in recent device list."""
        if self._old_devices_config_topics:
            for config_topic in (
                self._old_devices_config_topics - self._devices_config_topics
            ):
                ret_val = self._client.publish(config_topic, None, retain=True)
                _LOGGER.info(
                    "Removing retained topic %s, publish code %s", config_topic, ret_val
                )
        self._old_devices_config_topics = self._devices_config_topics
        self._config_topics_published = 0

    # def on_publish_gen(self, client, userdata, mid):
    #    _LOGGER.debug("On publish called, message id %s", mid)

    def on_message(self, client, userdata, message):
        """Process subscribed messages."""
        self._last_update = datetime.datetime.now(UTC_TIMEZONE)
        if message.topic == self._ha_status:
            status = message.payload.decode("utf-8")
            if status == "online":
                _LOGGER.info(
                    "HA online message received. Starting devices re-registration.%s",
                    message.retain,
                )
                self.start_bridge()
        elif message.topic == self._bridge_state_topic:
            _LOGGER.info("Bridge status message received")
            time.sleep(self._discovery_delay)
            self._cur_open_time = time.time()
            ret_val = self._client.subscribe(self._sub_cur_topic)
            _LOGGER.info(
                "Subscribed to retained values topic %s (%s)",
                self._sub_cur_topic,
                ret_val,
            )
            for restore_message in self._messages_to_restore_values:
                ret_val = self._client.publish(*restore_message)
                _LOGGER.info(
                    "Previous sensor values restored. Topic %s, publish code %s",
                    restore_message[0],
                    ret_val,
                )
                if self._print_payload:
                    _LOGGER.info(
                        "Previous sensor values restored. Payload %s",
                        restore_message[1],
                    )
            self._messages_to_restore_values = []
        elif message.topic == self._bridge_restart_topic:
            _LOGGER.info(
                "Restart requested, starting devices re-registration.%s",
                message.retain,
            )
            self.start_bridge()
        else:
            subtopics = message.topic.split("/")
            payload = message.payload.decode("utf-8")
            payload_struct = json.loads(payload) if len(payload) > 0 else None
            if subtopics[-1] == "config" and payload_struct:
                # _LOGGER.info("MQTT registration message received: MQTT topic %s, retain %s.", message.topic, message.retain)
                if (
                    "via_device" in payload_struct["device"]
                    and payload_struct["device"]["via_device"]
                    == self._bridge_indentifier
                ):
                    if self._print_payload:
                        _LOGGER.debug(
                            "MQTT registration message received: payload %s", payload
                        )
                    self._old_devices_config_topics.add(message.topic)
                    # _LOGGER.info("Added to previous refresh time self device list %s (%s) %s %s.", message.topic, len(self._old_devices_config_topics), payload_struct.get('time_stamp'), self._bridge_init_time)
                    if (
                        payload_struct.get("time_stamp")
                        and float(payload_struct["time_stamp"]) > self._bridge_init_time
                    ):
                        self._config_topics_published += 1
                        # _LOGGER.error("Counter increased to %s", self._config_topics_published)
            elif subtopics[-1] == "cur" and payload_struct:
                dev_eui = subtopics[-3]
                _LOGGER.debug("MQTT cached values received topic %s", message.topic)
                if self._print_payload:
                    _LOGGER.debug("MQTT cached values received payload %s", payload)
                _LOGGER.debug(
                    "MQTT cached values received payload time %s, bridge time %s, cached object %s, value cache %s",
                    payload_struct.get("time_stamp"),
                    self._bridge_init_time,
                    payload_struct.get("object"),
                    self._values_cache,
                )
                if (
                    payload_struct.get("time_stamp")
                    and float(payload_struct["time_stamp"]) < self._bridge_init_time
                ):
                    if dev_eui not in self._values_cache:
                        ret_val = self._client.publish(message.topic, None, retain=True)
                        _LOGGER.debug(
                            "Value cache removal topic %s published with code %s",
                            message.topic,
                            ret_val,
                        )
                    elif self._values_cache[dev_eui] == {}:
                        self._values_cache[dev_eui] = self.join_filtered_messages(
                            {}, payload_struct, self._top_level_msg_names
                        )
                        ret_val = self.publish_value_cache_record(
                            subtopics, "up", self._values_cache[dev_eui]
                        )
                cache_not_retrieved = len(
                    [dev_id for dev_id, val in self._values_cache.items() if val == {}]
                )
                _LOGGER.debug("MQTT nonprocessed device ids %s", cache_not_retrieved)
                if (
                    time.time() - self._cur_open_time > self._cur_age
                    or cache_not_retrieved == 0
                ):
                    ret_val = self._client.unsubscribe(self._sub_cur_topic)
                    _LOGGER.warning(
                        "MQTT unsubscribed from %s(%s)(%s)(%s)",
                        self._sub_cur_topic,
                        ret_val,
                        cache_not_retrieved,
                        time.time() - self._cur_open_time,
                    )
            elif subtopics[-1] == "up" and payload_struct:
                dev_eui = subtopics[-3]
                if (
                    not payload_struct.get("time_stamp")
                    and dev_eui in self._values_cache
                ):
                    self._values_cache[dev_eui] = self.join_filtered_messages(
                        self._values_cache[dev_eui],
                        payload_struct,
                        self._top_level_msg_names,
                    )
                    # _LOGGER.error("%s joined (o) payload %s", dev_eui, self._values_cache[dev_eui])
                    ret_val = self.publish_value_cache_record(
                        subtopics, "cur", self._values_cache[dev_eui], retain=True
                    )

        if (
            len(self._devices_config_topics) > 0
            and self._config_topics_published > 0
            and self._config_topics_published >= len(self._devices_config_topics)
        ):
            _LOGGER.debug(
                "All configuration messages sent out received %s(%s), config %s",
                self._config_topics_published,
                len(self._devices_config_topics),
                len(self._old_devices_config_topics - self._devices_config_topics),
            )
            self.clean_up_disappeared()
            ret_val = self._client.publish(
                self._bridge_state_topic, '{"state": "online"}', retain=True
            )
            _LOGGER.debug(
                "Bridge state turned on. MQTT topic %s, publish code %s",
                self._bridge_state_topic,
                ret_val,
            )

    def publish_value_cache_record(
        self, topic_array, topic_suffix, payload_struct, retain=False
    ):
        """Publish sensor value to values cache message."""
        topic_array[-1] = topic_suffix
        payload_struct["time_stamp"] = time.time()
        publish_topic = "/".join(topic_array)
        ret_val = self._client.publish(
            publish_topic, json.dumps(payload_struct), retain=retain
        )
        _LOGGER.debug(
            "MQTT cached values related topic %s published with code %s",
            publish_topic,
            ret_val,
        )
        if self._print_payload:
            _LOGGER.debug(
                "MQTT cached values related payload %s published with code %s",
                payload_struct,
                ret_val,
            )
        return ret_val

    def join_filtered_messages(self, message_o, message_n, levels_filter):
        """Join 2 payloads keeping all level data and recent values from message_n."""
        if isinstance(levels_filter, list):
            filtered = [{}]
            for level_filter in levels_filter[0]:
                message_o_r = message_o[0].get(level_filter) if message_o else None
                message_n_r = message_n[0].get(level_filter) if message_n else None
                if not message_o_r and not message_n_r:
                    continue
                filtered[0][level_filter] = self.join_filtered_messages(
                    message_o_r, message_n_r, levels_filter[0].get(level_filter)
                )
        elif levels_filter == {}:
            filtered = message_n if message_n else message_o
        else:
            filtered = {}
            for level_filter in levels_filter:
                message_o_r = message_o.get(level_filter) if message_o else None
                message_n_r = message_n.get(level_filter) if message_n else None
                if not message_o_r and not message_n_r:
                    continue
                filtered[level_filter] = self.join_filtered_messages(
                    message_o_r, message_n_r, levels_filter.get(level_filter)
                )
        return filtered

    def get_sensor_statistics(self):
        """Get recent sensor statistics for integration sensor entities."""
        return {
            STATISTICS_SENSORS: self._dev_sensor_count,
            STATISTICS_DEVICES: self._dev_count,
            STATISTICS_UPDATED: self._last_update,
        }

    def get_discovery_topic(self, dev_id, sensor, device, dev_conf):
        """Prepare sensor discovery topic based on integration type/device class."""
        if not sensor.get("integration"):
            mqtt_integration = None
            device_class = sensor["entity_conf"].get("device_class")
            if device_class:
                if device_class in [member.value for member in BinarySensorDeviceClass]:
                    mqtt_integration = "binary_sensor"
                if device_class in [member.value for member in SensorDeviceClass]:
                    mqtt_integration = "sensor"
                if device_class in [member.value for member in HumidifierDeviceClass]:
                    mqtt_integration = "humidifier"
                if not mqtt_integration:
                    mqtt_integration = "sensor"
                    _LOGGER.error(
                        "Could not detect integration by device class %s for dev_eui %s/%s, set to 'sensor'",
                        device_class,
                        dev_conf["dev_eui"],
                        id,
                    )
            else:
                mqtt_integration = "sensor"
                _LOGGER.error(
                    "No device class set for dev_eui %s/%s and no integration specified, set to 'sensor'",
                    dev_conf["dev_eui"],
                    dev_id,
                )
        else:
            mqtt_integration = sensor.get("integration")
        return f"{self._discovery_prefix}/{mqtt_integration}/{dev_conf['dev_eui']}/{dev_id}/config"

    def get_conf_data(self, dev_id, sensor, device, dev_conf):
        """Prepare discovery payload."""
        discovery_topic = self.get_discovery_topic(dev_id, sensor, device, dev_conf)
        status_topic = f"application/{self._application_id}/device/{dev_conf['dev_eui']}/event/{sensor.get('data_event') if sensor.get('data_event') else 'up'}"
        comand_topic = f"application/{self._application_id}/device/{dev_conf['dev_eui']}/command/down"
        discovery_config = sensor["entity_conf"]
        discovery_config["device"] = device
        discovery_config["device"]["name"] = (
            dev_conf["dev_name"] if dev_conf["dev_name"] else "0x" + dev_conf["dev_eui"]
        )
        if not discovery_config["device"].get("identifiers"):
            discovery_config["device"]["identifiers"] = [
                to_lower_case_no_blanks(BRIDGE_VENDOR + "_" + dev_conf["dev_eui"])
            ]
            discovery_config["device"]["via_device"] = self._bridge_indentifier
            discovery_config["availability"] = self._availability_element
        discovery_config["origin"] = self._origin
        if not discovery_config.get("state_topic"):
            discovery_config["state_topic"] = status_topic
        elif discovery_config.get("state_topic") == "{None}":
            del discovery_config["state_topic"]
        discovery_config["name"] = (
            dev_conf["measurement_names"][dev_id]
            if dev_conf["measurement_names"].get(dev_id)
            else dev_id
        )
        if not discovery_config.get("unique_id"):
            discovery_config["unique_id"] = to_lower_case_no_blanks(
                BRIDGE_VENDOR + "_" + dev_conf["dev_eui"] + "_" + dev_id
            )
        if not discovery_config.get("object_id"):
            discovery_config["object_id"] = to_lower_case_no_blanks(
                dev_conf["dev_eui"] + "_" + dev_id
            )
        for key in list(discovery_config):
            value = discovery_config[key]
            if not isinstance(value, str):
                continue
            if value == "{None}":
                del discovery_config[key]
            if value == "{command_topic}":
                discovery_config[key] = comand_topic
            if value == "{status_topic}":
                discovery_config[key] = status_topic
            if "{dev_eui}" in value:
                discovery_config[key] = value.replace( "{dev_eui}", dev_conf["dev_eui"] )
        discovery_config["enabled_by_default"] = True
        if self._bridge_init_time:
            discovery_config["time_stamp"] = self._bridge_init_time + 1
        else:
            discovery_config["time_stamp"] = time.time()
        return {
            "discovery_config_struct": discovery_config,
            "discovery_config": json.dumps(discovery_config),
            "discovery_topic": discovery_topic,
            "status_topic": status_topic,
            "comand_topic": comand_topic,
        }

    def close(self):
        """Close recent session."""
        self._client.loop_stop()
        self._client.disconnect()
