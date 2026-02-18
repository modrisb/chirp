"""The ChirpStack LoRaWAN Integration - mqtt interface."""
from __future__ import annotations

import datetime
import json
import logging
import re
import hashlib
import threading
import time
from zoneinfo import ZoneInfo

import paho.mqtt.client as mqtt

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
    CONF_MQTT_CHIRPSTACK_PREFIX,
    CONF_OPTIONS_RESTORE_AGE,
    CONF_OPTIONS_START_DELAY,
    CONNECTIVITY_DEVICE_CLASS,
    ENTITY_CATEGORY_DIAGNOSTIC,
    CONF_APPLICATION_ID,
    CONF_MQTT_SERVER,
    CONF_MQTT_PORT,
    CONF_MQTT_DISC,
    WARMSG_DEVCLS_REMOVED,
    BRIDGE_LOGLEVEL_ID,
    BRIDGE_LOGLEVEL_NAME,
    CONF_OPTIONS_ONLINE_PER_DEVICE,
    CONF_OPTIONS_LOG_LEVEL,
    CONF_OPTIONS_EXPIRE_AFTER,
    DEFAULT_OPTIONS_LOG_LEVEL,
    DEFAULT_OPTIONS_EXPIRE_AFTER,
    DEFAULT_OPTIONS_ONLINE_PER_DEVICE,
    DEFAULT_OPTIONS_START_DELAY,
    DEFAULT_OPTIONS_RESTORE_AGE,
)
INTEGRATION_BINARY_SENSOR = "binary_sensor"
INTEGRATION_BUTTON = "button"
INTEGRATION_SELECT = "select"

from .grpc import ChirpGrpc

_LOGGER = logging.getLogger(__name__)

UTC_TIMEZONE = ZoneInfo("UTC")


def to_lower_case_no_blanks(e_name):
    """Change string to lower case and replace blanks with _ ."""
    return e_name.lower().replace(" ", "_")

def generate_unique_id(configuration):
    """Create untegration unique id based on api/mqtt servers configurations."""
    u_id = "".join(
        [
            str(configuration[id_key])
            for id_key in (
                CONF_APPLICATION_ID,
                CONF_MQTT_SERVER,
                CONF_MQTT_PORT,
                CONF_MQTT_DISC,
                CONF_MQTT_CHIRPSTACK_PREFIX,
            )
        ]
    )
    unique_id = f"{hashlib.md5(u_id.encode('utf-8')).hexdigest()}"
    return unique_id

def convert_ret_val(ret_val):
    """Convert PAHO MQTT client api return codes to string, empty for 0(OK) return code."""
    if isinstance(ret_val, tuple):
        if ret_val[0]:
            return f", return code ({ret_val[0]},{ret_val[1]})"
        else:
            return ""
    else:
        if ret_val.rc:
            return f", return code ({ret_val.rc},{ret_val.mid})"
        else:
            return ""

class ChirpToHA:
    """ChirpStack LoRaWAN MQTT interface."""

    def __init__(
        self, config, version, classes, grpc_client: ChirpGrpc, connectivity_check_only=False
    ) -> None:
        """Open connection to HA MQTT server and initialize internal variables."""
        self._config = config
        self._version = version
        self._application_id = grpc_client._application_id
        self._unique_id = generate_unique_id(self._config)
        self._grpc_client: ChirpGrpc = grpc_client
        self._host = self._config.get(CONF_MQTT_SERVER)
        self._port = self._config.get(CONF_MQTT_PORT)
        self._user = self._config.get(CONF_MQTT_USER)
        self._pwd = self._config.get(CONF_MQTT_PWD)
        self._classes = classes
        self._dev_sensor_count = 0
        self._dev_count = 0
        self._last_update = None
        self._discovery_prefix = self._config.get(CONF_MQTT_DISC)
        self._chirpstack_prefix = self._config.get(CONF_MQTT_CHIRPSTACK_PREFIX)
        if self._chirpstack_prefix and not self._chirpstack_prefix.endswith("/"):
            self._chirpstack_prefix += "/"

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

        self._client.on_connect = self.on_connect
        self._client.username_pw_set(self._user, self._pwd)
        self._client.connect(self._host, self._port)
        self._origin = {
            "name": BRIDGE_VENDOR,
            "sw_version": self._version,
        }
        self._bridge_indentifier = to_lower_case_no_blanks(
            f"{BRIDGE_VENDOR} {BRIDGE} {self._unique_id}"
        )
        self._ha_online_event = threading.Event()
        self._cur_delay_event = threading.Event()
        self._dev_check_event = threading.Event()
        self._bridge_init_time = None
        self._cur_open_time = None
        self._live_on = False
        self._expire_after = self._config.get(CONF_OPTIONS_EXPIRE_AFTER, DEFAULT_OPTIONS_EXPIRE_AFTER)
        self._bridge_state_received = False
        self._per_device_chk_interval = float(self._config.get(CONF_OPTIONS_ONLINE_PER_DEVICE, DEFAULT_OPTIONS_ONLINE_PER_DEVICE))
        self._per_device_online = self._per_device_chk_interval!=0
        self._cur_opened_count = 0
        self._discovery_delay = self._config.get(CONF_OPTIONS_START_DELAY, DEFAULT_OPTIONS_START_DELAY)
        self._cur_age = self._config.get(CONF_OPTIONS_RESTORE_AGE, DEFAULT_OPTIONS_RESTORE_AGE)
        self._devices_config_topics = set()
        self._old_devices_config_topics = set()
        self._messages_to_restore_values = []
        self._top_level_msg_names = None
        self._values_cache = {}
        self._config_topics_published = 0
        self._bridge_config_topics_published = -1
        self._initialize_topic = f"{self._chirpstack_prefix}application/{self._application_id}/status"
        self._bridge_state_topic = f"{self._chirpstack_prefix}application/{self._application_id}/bridge/status"
        self._bridge_live_topic = f"{self._chirpstack_prefix}application/{self._application_id}/bridge/live"
        self._bridge_restart_topic = (
            f"{self._chirpstack_prefix}application/{self._application_id}/bridge/restart"
        )
        self._ha_status = f"{self._discovery_prefix}/status"
        self._sub_cur_topic = f"{self._chirpstack_prefix}application/{self._application_id}/device/+/event/cur"
        _LOGGER.info(
            "Connected to MQTT at %s:%s as %s",
            self._config.get(CONF_MQTT_SERVER),
            self._config.get(CONF_MQTT_PORT),
            self._config.get(CONF_MQTT_USER),
        )
        self._client.on_message = self.on_message

        self.subscribe(self._initialize_topic)
        self.subscribe(self._ha_status)
        self.subscribe(self._bridge_live_topic)
        self._availability_element = [
            {
                "topic": self._bridge_state_topic,
                "value_template": "{{ value_json.state }}",
            }
        ]

        if not connectivity_check_only:
            self._wait_for_ha_online = threading.Thread(target=self.ha_online_waiter)
            self._wait_for_dev_check = threading.Thread(target=self.dev_check_waiter)
            self._wait_for_cur = threading.Thread(target=self.cur_waiter)

            self.publish( self._initialize_topic, "initialize" )
            _LOGGER.info(
                "Bridge setup 'initialize' message published",
            )
        else:
            rc = self._client.loop_read(1)

    def on_connect(self, client, userdata, connect_flags, reason_code, properties):
        """MQTT api connection callback: throws error for failure cases."""
        self._client.on_connect = None
        if reason_code.is_failure:
            raise Exception(f"MQTT connection failed: {reason_code.value} - '{reason_code}'")

    def subscribe(self, topic):
        """MQTT subscribe api wrapper: throws error for failure cases."""
        ret_val = self._client.subscribe(topic)
        ex_message = convert_ret_val(ret_val)
        if ex_message != "":
            raise Exception(f"MQTT subscribe failed: '{ex_message}'")
        _LOGGER.detail(
            "MQTT subscribed to topic %s", topic,
        )
        return ret_val

    def unsubscribe(self, topic):
        """MQTT unsubscribe api wrapper: throws error for failure cases."""
        ret_val = self._client.unsubscribe( topic )
        ex_message = convert_ret_val(ret_val)
        if ex_message != "":
            raise Exception(f"MQTT unsubscribe failed: '{ex_message}'")
        _LOGGER.detail(
            "MQTT unsubscribed from topic %s", topic,
        )
        return ret_val

    def publish(self, topic, message, retain=False):
        """MQTT publish api wrapper: throws error for failure cases."""
        ret_val = self._client.publish( topic, message, retain=retain )
        ex_message = convert_ret_val(ret_val)
        if ex_message != "":
            raise Exception(f"MQTT publish failed: '{ex_message}'")
        _LOGGER.detail(
            "MQTT message published: topic %s, payload %s, retain=%s", topic, message, retain
        )
        return ret_val

    def ha_online_waiter(self): # to start bridge if homeassistant/status message is not received within discovery timeout
        """Thread app to send HA online message after specified time."""
        if not self._ha_online_event.wait(self._discovery_delay+0.1):
            self._ha_online_event.set()
            self.publish( self._initialize_topic, "configure" )
            _LOGGER.debug("%ss timeout expired, but no HA online message received, bridge setup 'configure' message published",
                          self._discovery_delay)

    def dev_check_waiter(self): # to periodically start device status update
        """Thread app to send refresh device live status message after specified time in infinite loop."""
        while not self._dev_check_event.is_set():
            if not self._dev_check_event.wait(self._per_device_chk_interval*60+0.1):
                self.publish( self._bridge_live_topic, "start" )

    def cur_waiter(self): # close time window for cur message processing
        """Thread app to close cur window after specified time, prepare thread for next time run."""
        if not self._cur_delay_event.wait(self._cur_age+0.1):
            time_delta = self._cur_open_time + self._cur_age - time.time()
            while time_delta > 0 and not self._cur_delay_event.wait(time_delta):
                time_delta = self._cur_open_time + self._cur_age - time.time()
            _LOGGER.debug("Time to stop cur message watch")
            self.disable_cur()
            self._wait_for_cur = threading.Thread(target=self.cur_waiter)

    def start_bridge(self):
        """Start Lora bridge registration within HA MQTT."""

        bridge_publish_data = self.get_conf_data(
            BRIDGE_STATE_ID,
            {  #   'entities':
                "integration": INTEGRATION_BINARY_SENSOR,
                "entity_conf": {
                    "state_topic": self._bridge_state_topic,
                    "value_template": "{{ value_json.state }}",
                    "default_entity_id": to_lower_case_no_blanks(
                        f"{INTEGRATION_BINARY_SENSOR}.{BRIDGE_VENDOR} {BRIDGE} {BRIDGE_ENTITY_NAME}"
                    ),
                    "unique_id": to_lower_case_no_blanks(
                        f"{BRIDGE} {self._unique_id} {BRIDGE_ENTITY_NAME} {BRIDGE_VENDOR}"
                    ),
                    "device_class": CONNECTIVITY_DEVICE_CLASS,
                    "entity_category": ENTITY_CATEGORY_DIAGNOSTIC,
                    "payload_on": "online",
                    "payload_off": "offline",
                },
            },
            {  #   'device':
                "manufacturer": BRIDGE_VENDOR,
                "model": BRIDGE,
                "identifiers": [self._bridge_indentifier],
            },
            {  #   'dev_conf':
                "measurement_names": {BRIDGE_STATE_ID: BRIDGE_ENTITY_NAME},
                "dev_name": BRIDGE_NAME,
                "dev_eui": self._unique_id,
            },
        )

        self.publish(
            bridge_publish_data["discovery_topic"],
            bridge_publish_data["discovery_config"],
            retain=True,
        )
        _LOGGER.debug(
            "Bridge device connectivity sensor published"
        )
        self._bridge_config_topics_published = 1

        bridge_refresh_data = self.get_conf_data(
            BRIDGE_RESTART_ID,
            {  #   'entities':
                "integration": INTEGRATION_BUTTON,
                "entity_conf": {
                    "availability_mode": "all",
                    "state_topic": "{None}",
                    "command_topic": self._bridge_restart_topic,
                    "default_entity_id": to_lower_case_no_blanks(
                        f"{INTEGRATION_BUTTON}.{BRIDGE_VENDOR} {BRIDGE} {BRIDGE_RESTART_ID}"
                    ),
                    "unique_id": to_lower_case_no_blanks(
                        f"{BRIDGE} {self._unique_id} {BRIDGE_RESTART_NAME} {BRIDGE_VENDOR}"
                    ),
                    "device_class": "restart",
                    "payload_press": "",
                },
            },
            {  #   'device':
                "manufacturer": BRIDGE_VENDOR,
                "model": BRIDGE,
                "identifiers": [self._bridge_indentifier],
            },
            {  #   'dev_conf':
                "measurement_names": {BRIDGE_RESTART_ID: BRIDGE_RESTART_NAME},
                "dev_name": BRIDGE_NAME,
                "dev_eui": self._unique_id,
            },
        )
        self.publish(
            bridge_refresh_data["discovery_topic"],
            bridge_refresh_data["discovery_config"],
            retain=True,
        )
        _LOGGER.debug(
            "Bridge device restart button published"
        )
        self._bridge_config_topics_published += 1

        bridge_log_data = self.get_conf_data(
            BRIDGE_LOGLEVEL_ID,
            {  #   'entities':
                "integration": INTEGRATION_SELECT,
                "entity_conf": {
                    "availability_mode": "all",
                    "state_topic": self._bridge_state_topic,
                    "value_template": '{{ value_json.log_level | lower }}',
                    "command_topic": self._bridge_state_topic,
                    "command_template": '{"state": "online", "log_level": "{{ value }}"}',
                    "default_entity_id": to_lower_case_no_blanks(
                        f"{INTEGRATION_SELECT}.{BRIDGE_VENDOR} {BRIDGE} {BRIDGE_LOGLEVEL_ID}"
                    ),
                    "unique_id": to_lower_case_no_blanks(
                        f"{BRIDGE} {self._unique_id} {BRIDGE_LOGLEVEL_NAME} {BRIDGE_VENDOR}"
                    ),
                    "options": ["error", "warning", "info", "debug", "detail"],
                    "retain": True,
                },
            },
            {  #   'device':
                "manufacturer": BRIDGE_VENDOR,
                "model": BRIDGE,
                "identifiers": [self._bridge_indentifier],
            },
            {  #   'dev_conf':
                "measurement_names": {BRIDGE_LOGLEVEL_ID: BRIDGE_LOGLEVEL_NAME},
                "dev_name": BRIDGE_NAME,
                "dev_eui": self._unique_id,
            },
        )

        self.publish(
            bridge_log_data["discovery_topic"],
            bridge_log_data["discovery_config"],
            retain=True,
        )
        _LOGGER.debug(
            "Bridge device log select published"
        )
        self._bridge_config_topics_published += 1
        _LOGGER.info(
            "Bridge initialization: %s components published",
            self._bridge_config_topics_published,
        )

    def reload_devices(self):
        self._bridge_init_time = time.time()
        _LOGGER.info(
            "Bridge initialization time stamp %s",
            self._bridge_init_time,
        )

        device_sensors = self._grpc_client.get_current_device_entities()

        self._dev_sensor_count = 0
        self._dev_count = 0

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
                for conf_key in sensor_entity_conf_data["discovery_config_struct"].keys():
                    if conf_key.endswith("_template"):
                        value_templates.append(sensor_entity_conf_data["discovery_config_struct"][conf_key])
                devices_config_topics.add(sensor_entity_conf_data["discovery_topic"])
                self.publish(
                    sensor_entity_conf_data["discovery_topic"],
                    sensor_entity_conf_data["discovery_config"],
                    retain=True,
                )
                _LOGGER.info(
                    f"Discovery message published: device {dev_eui} sensor '{sensor_entity_conf_data["discovery_topic"].split("/")[1]}'"
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
            "%s value(s) restore request(s) queued", len(self._messages_to_restore_values)
        )
        _LOGGER.info(
            "Devices reloaded, %s device{s) and %s sensor(s) found",
            self._dev_count,
            self._dev_sensor_count,
        )

    def enable_cur(self):
        """Enable cur window for restoring previous device values or updating live status."""
        self._cur_open_time = time.time()
        if not self._cur_opened_count:
            ret_val = self.subscribe(self._sub_cur_topic)
            _LOGGER.info(
                "Subscribed to retained values topic%s at %s",
                convert_ret_val(ret_val),
                self._cur_open_time,
            )
            self._wait_for_cur.start()
            time.sleep(0)
        self._cur_opened_count += 1

    def disable_cur(self):
        """Disable cur window."""
        self._cur_opened_count = 0
        if not self._cur_opened_count:
            self._live_on = False
            self.unsubscribe(self._sub_cur_topic)
            _LOGGER.info(
                "Unsubscribed from retained values topic"
            )
            _LOGGER.debug(
                "Not processed retained devices %s, processing age %s(s)",
                len([dev_id for dev_id, val in self._values_cache.items() if val == {}]),
                time.time() - self._cur_open_time,
            )

    def get_device_status(self, dev_eui):
        """Check device live status based on ChirpStack server information via gRPC interface."""
        visibility = self._grpc_client.get_device_visibility_info(dev_eui)
        if visibility["last_seen"] and visibility["uplink_interval"]:
            status = "online" if time.time()-visibility["last_seen"]<=visibility["uplink_interval"] else "offline"
        else:
            status = "offline"
        _LOGGER.debug(
            "Device %s status now is %s (live status: %s, current time stamp %s)", dev_eui, status, visibility, time.time()
        )
        return status

    def clean_up_disappeared(self):
        """Remove retained config messages from mqtt server if not in recent device list."""
        if self._old_devices_config_topics:
            for config_topic in (
                self._old_devices_config_topics - self._devices_config_topics
            ):
                self.publish(config_topic, None, retain=True)
                _LOGGER.info(
                    "Removing retained topic %s", config_topic
                )
        self._old_devices_config_topics = self._devices_config_topics
        self._config_topics_published = 0

    def on_message(self, client, userdata, message):
        """Process subscribed messages."""
        self._last_update = datetime.datetime.now(UTC_TIMEZONE)
        payload = message.payload.decode("utf-8")
        _LOGGER.detail("MQTT message received: topic %s, payload %s, retain=%s", message.topic, payload, message.retain)
        if message.topic == self._bridge_state_topic:
            self._bridge_state_received = True
            _LOGGER.info("Bridge state message received")
            try:
                logging.getLogger().setLevel(json.loads(payload).get("log_level").upper())
            except Exception as error:
                _LOGGER.error("Bridge state message processing failed: %s", str(error))
        elif message.topic == self._bridge_restart_topic:
            _LOGGER.info(
                "Bridge restart requested"
            )
            self._bridge_config_topics_published = 0    # enables value restoration
            self.reload_devices()
        elif message.topic == self._bridge_live_topic:
            _LOGGER.debug("Bridge device live status update requested")
            if payload == "start":
                self._live_on = True
                self.enable_cur()
        elif message.topic == self._ha_status:
            if payload == "online":
                self._ha_online_event.set()
                self.publish( self._initialize_topic, "configure" )
                _LOGGER.info(
                    "HA online, continuing configuration"
                )
            elif payload == "offline":
                _LOGGER.info(
                    "HA offline message received",
                )

        elif message.topic == self._initialize_topic:
            _LOGGER.info(
                "Bridge setup '%s' message received",
                payload
            )
            if payload == "initialize":
                self._wait_for_ha_online.start()
                if self._per_device_online:
                    self._wait_for_dev_check.start()
                    _LOGGER.info("Periodic device check task started for %s minute(s) interval", self._per_device_chk_interval)
            else: # configure
                self.subscribe(self._bridge_state_topic)
                self.subscribe(self._bridge_restart_topic)
                self.subscribe(
                    f"{self._chirpstack_prefix}application/{self._application_id}/device/+/event/up"
                )
                self.subscribe(f"{self._discovery_prefix}/+/+/+/config")
                self.start_bridge()
                self.reload_devices()
        else:
            subtopics = message.topic.split("/")
            payload_struct = json.loads(payload) if len(payload) > 2 else None
            if payload_struct:
                time_stamp = payload_struct.get("time_stamp")
                _LOGGER.detail(f"Processing message with time stamp {time_stamp} for topic {message.topic} and payload {payload_struct}")

                if subtopics[-1] == "config":
                    if payload_struct.get("device"):
                        if (
                            "via_device" in payload_struct["device"]
                            and payload_struct["device"]["via_device"]
                            == self._bridge_indentifier
                        ):
                            _LOGGER.info(f"Registration message with time stamp {time_stamp} received for device {subtopics[2]} sensor {subtopics[1]}")
                            self._old_devices_config_topics.add(message.topic)
                            if (
                                time_stamp and float(time_stamp) >= self._bridge_init_time
                            ):
                                self._config_topics_published += 1
                        else:
                            self._bridge_config_topics_published -= 1
                elif subtopics[-1] == "cur":
                    dev_eui = subtopics[-3]
                    _LOGGER.info("Cached values received for device %s", dev_eui)
                    _LOGGER.debug(
                        "Cached values payload time %s, bridge time %s, cached object %s, value cache %s",
                        time_stamp,
                        self._bridge_init_time,
                        payload_struct.get("object"),
                        self._values_cache,
                    )
                    if (
                        time_stamp and float(time_stamp) < self._bridge_init_time
                    ):
                        if dev_eui not in self._values_cache:
                            self.publish(message.topic, None, retain=True)
                            _LOGGER.debug(
                                "Value cache removal topic %s published",
                                message.topic,
                            )
                        elif self._values_cache[dev_eui] == {} and time_stamp < self._cur_open_time:
                            ret_val = self.publish_value_cache_record(
                                subtopics, "up", dev_eui, payload_struct
                            )
                    if self._live_on and time_stamp < self._cur_open_time:
                        self.publish_value_cache_record(
                                subtopics, "cur", dev_eui, payload_struct
                            )
                    cache_not_retrieved = len(
                        [dev_id for dev_id, val in self._values_cache.items() if val == {}]
                    )
                    _LOGGER.debug("%s device(s) cached values not processed", cache_not_retrieved)
                elif subtopics[-1] == "up":
                    dev_eui = subtopics[-3]
                    if (
                        not time_stamp
                        and dev_eui in self._values_cache
                    ):
                        self._values_cache[dev_eui] = self.join_filtered_messages(
                            self._values_cache[dev_eui],
                            payload_struct,
                            self._top_level_msg_names,
                        )
                        self.publish_value_cache_record(
                            subtopics, "cur", dev_eui, payload_struct, retain=True
                        )
            else:
                _LOGGER.info(
                    "Ignoring topic %s with payload %s",
                    message.topic,
                    message.payload,
                )
        if (
            len(self._devices_config_topics) > 0
            and self._config_topics_published > 0
            and self._config_topics_published >= len(self._devices_config_topics)
        ):
            _LOGGER.info(
                "%s of %s configuration messages received, %s disappeared devices",
                self._config_topics_published,
                len(self._devices_config_topics),
                len(self._old_devices_config_topics - self._devices_config_topics),
            )
            self.clean_up_disappeared()
        if self._bridge_config_topics_published == 0:
            self._bridge_config_topics_published = -1
            time.sleep(self._discovery_delay)
            if not self._bridge_state_received:
                self.publish(
                    self._bridge_state_topic, f'{{"state": "online", "log_level": "{self._config.get(CONF_OPTIONS_LOG_LEVEL, DEFAULT_OPTIONS_LOG_LEVEL)}"}}', retain=True
                )
                _LOGGER.info(
                    "Bridge state turned on, log level %s",
                    self._config.get(CONF_OPTIONS_LOG_LEVEL, DEFAULT_OPTIONS_LOG_LEVEL),
                )
            self.enable_cur()
            for restore_message in self._messages_to_restore_values:
                self.publish(*restore_message)
                _LOGGER.info(
                    f"Previous sensor values restored for device {restore_message[0].split('/')[3]}",
                )
            self._messages_to_restore_values = []

    def publish_value_cache_record(
        self, topic_array, topic_suffix, dev_eui, payload_struct, retain=False
    ):
        """Publish sensor value to values cache message."""

        self._values_cache[dev_eui] = self.join_filtered_messages(
            self._values_cache[dev_eui],
            payload_struct,
            self._top_level_msg_names,
        )
        payload_struct = self._values_cache[dev_eui]

        if len(payload_struct) or topic_suffix == "cur":
            topic_int = topic_array.copy()
            topic_int[-1] = topic_suffix
            payload_struct["time_stamp"] = time.time()
            publish_topic = "/".join(topic_int)
            if topic_suffix == "cur" and self._per_device_online:
                payload_struct = payload_struct.copy()
                payload_struct["status"] = self.get_device_status(dev_eui)

            ret_val = self.publish(
                publish_topic, json.dumps(payload_struct), retain=retain
            )
            _LOGGER.debug(
                f"Cached values published for device {topic_int[3]} and topic {topic_suffix} {publish_topic}",
            )
        else:
            ret_val = (0,0)
        return ret_val

    def join_filtered_messages(self, message_o, message_n, levels_filter):
        """Join 2 payloads keeping all level data and recent values from message_n."""
        if isinstance(levels_filter, list):
            filtered = [{}]
            for level_filter in levels_filter[0]:
                message_o_r = message_o[0].get(level_filter) if message_o else None
                message_n_r = message_n[0].get(level_filter) if message_n else None
                if message_o_r==None and message_n_r==None:
                    continue
                filtered[0][level_filter] = self.join_filtered_messages(
                    message_o_r, message_n_r, levels_filter[0].get(level_filter)
                )
        elif levels_filter == {}:
            filtered = message_n if message_n!=None else message_o
        else:
            filtered = {}
            for level_filter in levels_filter:
                message_o_r = message_o.get(level_filter) if message_o else None
                message_n_r = message_n.get(level_filter) if message_n else None
                if message_o_r==None and message_n_r==None:
                    continue
                filtered[level_filter] = self.join_filtered_messages(
                    message_o_r, message_n_r, levels_filter.get(level_filter)
                )
        return filtered

    def get_discovery_topic(self, dev_id, sensor, device, dev_conf):
        """Prepare sensor discovery topic based on integration type/device class."""
        if not sensor.get("integration"):
            mqtt_integration = None
            device_class = sensor["entity_conf"].get("device_class")
            if device_class and self._classes:
                for integration in self._classes["integrations"]:
                    if device_class in self._classes.get(integration):
                        mqtt_integration = integration
                        break
                if not mqtt_integration:
                    mqtt_integration = "sensor"
                    _LOGGER.warning(
                        WARMSG_DEVCLS_REMOVED,
                        device_class,
                        dev_conf["dev_eui"],
                    )
                    del sensor["entity_conf"]["device_class"]
            else:
                mqtt_integration = "sensor"
                _LOGGER.info(
                    "No device class set for dev_eui %s/%s and no integration specified, set to 'sensor'",
                    dev_conf["dev_eui"],
                    dev_id,
                )
        else:
            mqtt_integration = sensor.get("integration")
        return f"{self._discovery_prefix}/{mqtt_integration}/{dev_conf['dev_eui']}/{dev_id}/config"

    def get_availability_element(self, dev_id, sensor, device, dev_conf):
        if self._per_device_online:
            availability_elements = self._availability_element.copy()
            for availability_element in availability_elements:
                availability_element["topic"] = f"{self._chirpstack_prefix}application/{self._application_id}/device/{dev_conf['dev_eui']}/event/cur"
            return availability_elements
        else:
            return self._availability_element

    def get_conf_data(self, dev_id, sensor, device, dev_conf):
        """Prepare discovery payload."""
        discovery_topic = self.get_discovery_topic(dev_id, sensor, device, dev_conf)
        status_topic = f"{self._chirpstack_prefix}application/{self._application_id}/device/{dev_conf['dev_eui']}/event/{sensor.get('data_event') if sensor.get('data_event') else 'up'}"
        comand_topic = f"{self._chirpstack_prefix}application/{self._application_id}/device/{dev_conf['dev_eui']}/command/down"
        discovery_config = sensor["entity_conf"].copy()
        discovery_config["device"] = device.copy()
        for key in list(discovery_config["device"]):
            if key.startswith("dev_eui"):
                if key == "dev_eui" + dev_conf["dev_eui"]:
                    for dev_key in discovery_config["device"][key]:
                        discovery_config["device"][dev_key] = discovery_config["device"][key][dev_key]
                del discovery_config["device"][key]
        if not discovery_config["device"].get("name"):
            discovery_config["device"]["name"] = (
                dev_conf["dev_name"] if dev_conf["dev_name"] else "0x" + dev_conf["dev_eui"]
            )
        if not discovery_config["device"].get("identifiers"):
            discovery_config["device"]["identifiers"] = [
                to_lower_case_no_blanks(BRIDGE_VENDOR + "_" + dev_conf["dev_eui"])
            ]
            discovery_config["device"]["via_device"] = self._bridge_indentifier
            discovery_config["availability"] = self.get_availability_element(dev_id, sensor, discovery_config["device"], dev_conf)
        discovery_config["origin"] = self._origin
        if not discovery_config.get("state_topic"):
            discovery_config["state_topic"] = status_topic
        if not discovery_config.get("name"):
            discovery_config["name"] = (
                dev_conf["measurement_names"][dev_id]
                if dev_conf["measurement_names"].get(dev_id)
                else dev_id
            )
        if not discovery_config.get("unique_id"):
            discovery_config["unique_id"] = to_lower_case_no_blanks(
                BRIDGE_VENDOR + "_" + dev_conf["dev_eui"] + "_" + dev_id
            )
        if not discovery_config.get("default_entity_id"):
            discovery_config["default_entity_id"] = to_lower_case_no_blanks(
                dev_conf["dev_eui"] + "_" + dev_id
            )
        if self._expire_after and discovery_config.get("uplink_interval") and not discovery_config.get("expire_after"):
            discovery_config["expire_after"] = discovery_config["uplink_interval"]
        for key in list(discovery_config):
            value = discovery_config[key]
            if key.startswith("dev_eui"):
                if key == "dev_eui" + dev_conf["dev_eui"]:
                    for dev_key in value:
                        discovery_config[dev_key] = value[dev_key]
                del discovery_config[key]
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
        if discovery_config.get("enabled_by_default")==None:
            discovery_config["enabled_by_default"] = True
        if self._bridge_init_time:
            discovery_config["time_stamp"] = self._bridge_init_time
        return {
            "discovery_config_struct": discovery_config,
            "discovery_config": json.dumps(discovery_config),
            "discovery_topic": discovery_topic,
            "status_topic": status_topic,
            "comand_topic": comand_topic,
        }

    def close(self):
        """Close recent session."""
        self._ha_online_event.set()
        self._cur_delay_event.set()
        self._dev_check_event.set()

        self._client.disconnect()
