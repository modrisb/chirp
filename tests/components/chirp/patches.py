"""Mocks for ChirpStack grpc api, paho mqtt, dukpy."""

import enum
import json
import logging
import math
from queue import Queue, ShutDown
import threading
import time

from homeassistant.config_entries import ConfigEntryState

_LOGGER = logging.getLogger(__name__)

MODEL_SIZES = [
    {
        "tenants": 2,
        "applications": 1,
        "devices": 2,
        "mqtt": 1,
        "grpc": 1,
        "publish": 1,
        "codec": 1,
        "subscribe": 1,
        "unsubscribe": 1,
        "gateways": 2,
        "single_tenant": -1,
    }
]

getdevcount = [0]

CODEC = [  # array of (no_of_sensors, "codec_code")
    (  # 0
        4,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {sensor{dev_no}:{entity_conf: {device_class: "gas"}},battery:{entity_conf: {value_template: "{{ value_json.batteryLevel }}",entity_category: "diagnostic",device_class: "battery",unit_of_measurement: "%",}},rssi:{entity_conf: {value_template: "{{ value_json.rxInfo[-1].rssi | int }}",entity_category: "diagnostic",device_class: "signal_strength",}},altitude:{entity_conf:{integration:"sensor", value_template: "{{ value_json.rxInfo[-1].location.altitude | int }}"}}}};}',
    ),
    (  # 1
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {device_class: "gas"}}}};}',
    ),
    (  # 2
        2,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},rssi:{data_event: "status",entity_conf: {value_template: "{{ value_json.rxInfo[-1].rssi | int }}",entity_category: "diagnostic",device_class: "signal_strength",}}}};}',
    ),
    (0, "function getHaDeviceInfo() {return {device:"),  # 3
    (  # 4
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: \'model1\',},// \nentities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}}}};}',
    ),
    (  # 5
        2,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter[0] }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},battery:{data_event: "status",entity_conf: {value_template: "{{ value_json.batteryLevel[-1]}}",entity_category: "diagnostic",device_class: "battery",unit_of_measurement: "%",}}}};}',
    ),
    (  # 6
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},}};}',
    ),
    (  # 7
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{integration:"climate",entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},}};}',
    ),
    (  # 8
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",state_class: "total_increasing",unit_of_measurement: "m³"}},}};}',
    ),
    (  # 9
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas001",state_class: "total_increasing",unit_of_measurement: "m³"}},}};}',
    ),
    (  # 10
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",command_topic:"{command_topic}",unit_of_measurement: "m³"}},}};}',
    ),
    (0, 'function getHaDeviceInf() {return {device:""}}'),  # 11
    (0, 'function getHaDeviceInfo() {retur {device:,""}}'),  # 12
    (0, "function getHaDeviceInfo() {return "),  # 13
    (  # 14
        0,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: \'model1\',},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: / \n"gas",state_class: "total_increasing",unit_of_measurement: "m³"}}}};}',
    ),
    (  # 15
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "humidifier",state_class: "total_increasing",unit_of_measurement: "m³"}},}};}',
    ),
    (  # 16
        1,
        "function getHaDeviceInfo() {return {device: {manufacturer: 'vendor0',model: \"model1\",},entities: {counter:{entity_conf: {value_template: '{{ value_json.object.counter }}'}},}};}",
    ),
    (  # 17
        1,
        "        function getHaDeviceInfo() {\
        return {\
            device: {\
            manufacturer: 'Milesight IoT Co., Ltd',\
            model: 'WT101'\
            },\
            entities: {\
            counter: {\
                integration: 'climate',\
                entity_conf: {\
                modes: ['auto', 'heat', 'off'],\
                mode_state_topic: '{status_topic}',\
                mode_state_template: '{% if (value_json.object.motor_position | int) == 0 %} offx {% else %} heatx {% endif %}',\
                current_temperature_topic: '{status_topic}',\
                current_temperature_template: '{{ (value_json.object.temperature | float) }}',\
                temperature_command_topic: '{command_topic}',\
                temperature_command_template: '{ \"devEui\": \"{dev_eui}\", \"confirmed\": true, \"fPort\": 85, \"object\": { \"temperature_target\": {{ value | float }},\"temperature_error\": 0.1 } }',\
                min_temp: 6,\
                max_temp: 30,\
                temp_step: 0.1\
                }\
            }\
            }\
        };\
        }\
        ",
    ),
    (  # 18
        1,
        "\
        function getHaDeviceInfo() {\
        return {\
            device: {\
            manufacturer: 'Milesight IoT Co., Ltd',\
            model: 'WT101'\
            },\
            entities: {\
            counter: {\
                integration: 'climate',\
                entity_conf: {\
                value_template: '{None}',\
                status_topic: '{None}',\
                modes: \"['auto', 'heat', 'off']\",\
                mode_state_topic: '{status_topic}',\
                mode_state_template: '{% if (value_json.object.motor_position | int) == 0 %} offx {% else %} heatx {% endif %}',\
                current_temperature_topic: '{status_topic}',\
                current_temperature_template: '{{ (value_json.object.temperature | float) }}',\
                temperature_command_topic: '{command_topic}',\
                temperature_command_template: '{ \"devEui\": \"{dev_eui}\", \"confirmed\": true, \"fPort\": 85, \"object\": { \"temperature_target\": {{ value | float }},\"temperature_error\": 0.1 } }',\
                min_temp: '6',\
                max_temp: '30',\
                temp_step: '0.1'\
                }\
            }\
            }\
        };\
        }\
        ",
    ),
    (  # 19
        0,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: \'model1\',},// \nentities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}}}};}',
    ),
    (  # 20
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {expire_after: "{None}",device_class: "gas"}}}};}',
    ),
    (  # 21
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",dev_euidev_eui0:{model:"model1a"}},entities: {counter:{entity_conf: {dev_euidev_eui0:{device_class:"water"}, expire_after: "{None}",device_class: "gas"}}}};}',
    ),
    (  # 22
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas001",state_class: "total_increasing",unit_of_measurement: "m³", enabled_by_default:false}},}};}',
    ),
    (  # 23
        6,
        "\
        function getHaDeviceInfo() {\
        return {\
            device: {\
            manufacturer: 'M0',\
            model: 'zeroentityvalues'\
            },\
            entities: {\
            s0: {entity_conf: {value_template: '{{ value_json.object.s0 }}' }},\
            s1: {entity_conf: {value_template: '{{ value_json.object.s1 }}' }},\
            l0: {entity_conf: {value_template: '{{ value_json.object.l0 }}' }},\
            l1: {entity_conf: {value_template: '{{ value_json.object.l1 }}' }},\
            i0: {entity_conf: {value_template: '{{ value_json.object.i0 }}' }},\
            i1: {entity_conf: {value_template: '{{ value_json.object.i1 }}' }},\
            }\
        };\
        }\
        ",
    ),
    (  # 24
        2,
        "\
        ",
    ),
]


def get_size(type_name):
    """Get test mock parameters."""
    if type_name == "sensors":
        return 0 if get_size("disabled") else CODEC[get_size("codec")][0]
    if type_name == "idevices":
        if get_size("disabled"):
            return 0
        return get_size("devices") if CODEC[get_size("codec")][0] else 0
    return MODEL_SIZES[0][type_name]


def set_size(
    tenants=2,
    applications=1,
    devices=2,
    mqtt=1,
    grpc=1,
    publish=1,
    codec=1,
    disabled=False,
    subscribe=1,
    unsubscribe=1,
    gateways=2,
    single_tenant=-1,
):
    """Set test mock parameters."""
    MODEL_SIZES[0]["tenants"] = tenants
    MODEL_SIZES[0]["applications"] = applications
    MODEL_SIZES[0]["devices"] = devices
    MODEL_SIZES[0]["mqtt"] = mqtt
    MODEL_SIZES[0]["grpc"] = grpc
    MODEL_SIZES[0]["publish"] = publish
    MODEL_SIZES[0]["codec"] = codec
    MODEL_SIZES[0]["disabled"] = disabled
    MODEL_SIZES[0]["subscribe"] = subscribe
    MODEL_SIZES[0]["unsubscribe"] = unsubscribe
    MODEL_SIZES[0]["gateways"] = gateways
    MODEL_SIZES[0]["single_tenant"] = single_tenant
    getdevcount[0] = 0


class message:
    """Class to represent mqtt message."""

    def __init__(self, topic, payload, qos=0, retain=False) -> None:
        """Initialize message, ensure payload encoding."""
        self.topic = topic
        if payload is not None and hasattr(payload, "encode"):
            self.payload = payload.encode()
        else:
            self.payload = payload
        self.qos = qos
        self.retain = retain


class mqtt:
    """Mock paho mqtt interface."""

    class CallbackAPIVersion(enum.Enum):
        """Defined the arguments passed to all user-callback."""

        VERSION1 = 1
        VERSION2 = 2

    class Client:
        """Mock paho mqtt Client class."""

        hass = None
        config = None
        _publish_count = 0
        _published = []
        _subscribed = set()
        _connected = False
        on_message = None
        on_connect = None
        on_publish = None
        _stat_start_time = 0
        _stat_dev_eui = None
        stat_devices = 0
        stat_sensors = 0
        _publish_queue = None
        _open_count = 0
        _run_loop = True
        _block_loop = True

        def __init__(self, version) -> None:
            """Mock Client class initialization."""
            self._loop_thread_inner = threading.Thread(target=self._loop_forever)

        def __new__(cls, version):
            """Implement singleton for test."""
            if not hasattr(cls, "instance"):
                cls.instance = super(mqtt.Client, cls).__new__(cls)
            return cls.instance

        def username_pw_set(self, user, pwd):
            """Mock username_pw_set function."""

        def connect(self, host, port):
            """Mock connect function, raise exception if requested."""
            _LOGGER.info("MQTT connect %s", self._open_count)
            if not self._connected:
                if self._open_count == 0:
                    self._published = []
                    self._subscribed = set()
                    self.on_publish = None
                    self._stat_start_time = 0
                    self._stat_dev_eui = None
                    self.stat_devices = 0
                    self.stat_sensors = 0
                    self._publish_queue = Queue()
                    self._connected = True
                    self._publish_count = 0
                    self._run_loop = True
                    self._block_loop = True
            self._open_count = self._open_count + 1
            return 0

        def publish(self, topic, payload, qos=0, retain=True):
            """Mock publish function, raise exception if requested."""
            self._publish_queue.put((topic, payload, qos, retain))
            self._publish_count += 1
            self._published.append((topic, payload, qos, retain))
            ret_val = lambda: None  # noqa: E731
            ret_val.rc = 0 if get_size("publish") else 1
            ret_val.mid = self._publish_count
            return ret_val

        def loop_start(self):
            """Mock loop_start function."""
            self._block_loop = False
            self.loop_forever()
            return 0

        def loop_read(self, max_packets: int = 1):
            """Mock loop_read function."""
            return self.loop()

        def loop_misc(self):
            """Mock loop_misc function."""
            return self.loop()

        def loop(self, timeout: float = 1):
            """Mock loop function."""
            if self.on_connect:
                reason_code = lambda: None  # noqa: E731
                reason_code.is_failure = get_size("mqtt") == 0
                reason_code.value = 135
                self.on_connect(None, None, None, reason_code, None)
            #self.disconnect()
            return 0

        def loop_forever(self):
            """Mock loop_forever function."""
            if self.on_connect:
                reason_code = lambda: None  # noqa: E731
                reason_code.is_failure = get_size("mqtt") == 0
                reason_code.value = 135
                self.on_connect(None, None, None, reason_code, None)
            if not self._loop_thread_inner.is_alive():
                self._loop_thread_inner.start()
                if self._block_loop:
                    self._loop_thread_inner.join()
            if not get_size("publish") and self._publish_count > 0:
                raise Exception("MQTT request processing error")  # pylint: disable=broad-exception-raised  # noqa: TRY002

        def _loop_forever(self):
            """Mock loop_forever function."""
            while self._run_loop:
                try:
                    msg = self._publish_queue.get()
                except ShutDown:
                    break
                if msg[0] is None and msg[1] is None:
                    break
                if not get_size("publish") and self._publish_count > 0:
                    break
                sub_topics = msg[0].split("/")
                if (
                    sub_topics[-1] == "restart"
                ):  # or (sub_topics[0] != "application" and sub_topics[-1] == "status"): # allowing single online message
                    self.reset_stats()
                if (
                    sub_topics[-1] == "status" and msg[1] == "configure"
                ):  # reset on configure request
                    self.reset_stats()
                if (
                    self.on_message
                    and msg[1] is not None
                    and sub_topics[-1] in self._subscribed
                ):
                    self.on_message(self, None, message(msg[0], msg[1], msg[2], msg[3]))
                if sub_topics[-1] == "config" and sub_topics[2].startswith("dev"):
                    payload_struct = (
                        json.loads(msg[1]) if msg[1] and len(msg[1]) > 0 else None
                    )
                    if payload_struct:
                        if self._stat_start_time != payload_struct.get("time_stamp"):
                            self.reset_stats()
                            self._stat_start_time = payload_struct.get("time_stamp")
                        self.stat_sensors += 1
                        if self._stat_dev_eui != sub_topics[2]:
                            self._stat_dev_eui = sub_topics[2]
                            self.stat_devices += 1
                self._publish_queue.task_done()
            return 0

        def subscribe(self, topic):
            """Mock subscribe function."""
            sub_topics = topic.split("/")
            self._subscribed.add(sub_topics[-1])
            return (0, 0) if get_size("subscribe") else (1, 1)

        def unsubscribe(self, topic):
            """Mock unsubscribe function."""
            return (0, 0) if get_size("unsubscribe") else (1, 1)

        def loop_stop(self):
            """Mock loop_stop function."""
            return 0

        def disconnect(self):
            """Mock disconnect function."""
            if self._open_count == 1:
                if self._connected:
                    self._run_loop = False
                    self._connected = False
                    self._publish_queue.shutdown(immediate=True)
                    if self._loop_thread_inner.is_alive():
                        self._loop_thread_inner.join()
            if self._open_count > 0:
                self._open_count = self._open_count - 1
            return 0

        # for testing only
        def get_published(self, keep_history=False):
            """Implement published message retrieval and buffer cleanup."""
            current = self._published
            if not keep_history:
                self._published = []
            return current

        def close(self):
            """Implement mock close function."""
            self.disconnect()

        def reset_stats(self):
            """Reset device/sensor counters - test extension."""
            self._stat_start_time = None
            self.stat_devices = 0
            self.stat_sensors = 0
            self._stat_dev_eui = None

        def wait_empty_queue(self):
            """Blocks till loop_forever is executed - test extension."""
            if self._connected:
                self._publish_queue.join()

        def reset_mock(self):
            """Reset mock - test extension."""
            set_size()
            while self._open_count > 0:
                self.disconnect()

        def check_mock_status(self):
            """Check mock status - test extension."""
            return (
                self._publish_queue
                and self._publish_queue.qsize() == 0
                and self._open_count == 0
                and not self._loop_thread_inner.is_alive()
            )


class api:
    """ChirpStack api mock implementation."""

    class TenantServiceStub:
        """TenantServiceStub class mock implementation."""

        def __init__(self, channel) -> None:
            """TenantServiceStub class init mock implementation."""

        def List(self, listTenantsReq, metadata):
            """Get mocked list tenants request response."""
            no_of_tenants = get_size("tenants")
            request = lambda: None  # noqa: E731
            if listTenantsReq.limit is not None:
                request.result = []
                for i in range(no_of_tenants):
                    tenant = lambda: None  # noqa: E731
                    tenant.name = f"TenantName{i}"
                    tenant.id = f"TenantId{i}"
                    request.result.append(tenant)

            request.total_count = no_of_tenants
            return request

        def Create(self, createTenantReq, metadata):
            """Get mocked create tenant request response."""
            no_of_tenants = get_size("tenants") + 1
            MODEL_SIZES[0]["tenants"] = no_of_tenants
            request = lambda: None  # noqa: E731
            request.id = f"TenantId{no_of_tenants}"
            return request

    class ListTenantsRequest:
        """Prepare list tenants request object, initialize only used in test fields."""

        def __init__(self, limit=None, offset=None, search=None, user_id=None) -> None:
            """Prepare list tenants request object, initialize only used in test fields."""
            self.limit: int | None = limit
            self.offset: int | None = offset
            self.search: str | None = search
            self.user_id: str | None = user_id

    def CreateTenantRequest():
        """Prepare create tenant request object, initialize only used in test fields."""
        request = lambda: None  # noqa: E731
        request.tenant = lambda: None
        request.tenant.name = None
        request.tenant.can_have_gateways = None
        request.tenant.max_gateway_count = None
        return request

    class ApplicationServiceStub:
        """Application service implementation."""

        def __init__(self, channel) -> None:
            """Application service initialization implementation."""

        def List(self, listApplicationsReq, metadata):
            """Get mocked applications list request response."""
            no_of_applications = get_size("applications")
            request = lambda: None  # noqa: E731
            if listApplicationsReq.limit is not None:
                request.result = []
                for i in range(no_of_applications):
                    appl = lambda: None  # noqa: E731
                    appl.name = f"ApplicationName{i}"
                    appl.id = f"ApplicationId{i}"
                    ii = (
                        i
                        if get_size("single_tenant") < 0
                        else get_size("single_tenant")
                    )
                    appl.tenant_id = f"TenantId{ii}"  # to enable app search by tenant id and have sevearl apps returned
                    if listApplicationsReq.tenant_id == appl.tenant_id:
                        request.result.append(appl)
            request.total_count = no_of_applications
            return request

        def Get(self, getApplicationReq, metadata):
            """Get mocked applications list request response."""
            no_of_applications = get_size("applications")
            for i in range(no_of_applications):
                if getApplicationReq.id == f"ApplicationId{i}":
                    request = lambda: None  # noqa: E731
                    request.application = lambda: None
                    request.application.id = getApplicationReq.id
                    request.application.tenant_id = f"TenantId{i}"
                    return request
            raise Exception("Application does not exist")  # pylint: disable=broad-exception-raised  # noqa: TRY002

        def Create(self, listApplicationsReq, metadata):
            """Get mocked applications list request response."""
            no_of_applications = get_size("applications") + 1
            MODEL_SIZES[0]["applications"] = no_of_applications
            request = lambda: None  # noqa: E731
            request.id = f"ApplicationId{no_of_applications}"
            return request

    @staticmethod
    def ListApplicationsRequest(tenant_id=None):
        """List applications request object."""
        request = lambda: None  # noqa: E731
        request.limit = None
        request.tenant_id = tenant_id
        return request

    @staticmethod
    def GetApplicationRequest(id=None):
        """Get application description by ID."""
        request = lambda: None  # noqa: E731
        request.id = id
        return request

    @staticmethod
    def CreateApplicationRequest():
        """Create application request."""
        request = lambda: None  # noqa: E731
        request.application = lambda: None
        request.application.name = None
        request.application.tenant_id = None
        return request

    class DeviceServiceStub:
        """Device service implementation."""

        def __init__(self, channel) -> None:
            """Device service initialization implementation."""

        def List(self, listDevicesReq, metadata=None):
            """Get mocked list devices request response."""
            no_of_devices = get_size("devices")
            request = lambda: None  # noqa: E731
            if listDevicesReq.limit is not None:
                request.result = []
                for i in range(no_of_devices):
                    device = lambda: None  # noqa: E731
                    device.dev_eui = f"dev_eui{i}"
                    device.name = f"device_name{i}"
                    device.device_profile_id = f"device_profile_id{i}"
                    device.device_status = lambda: None
                    device.device_status.battery_level = 95
                    device.device_status.external_power_source = (i % 2) == 1
                    device.last_seen_at = ""
                    request.result.append(device)
            request.total_count = no_of_devices
            return request

        def Get(self, deviceReq, metadata):
            """Get mocked device request response."""
            dev_no = int(deviceReq.dev_eui[7:])
            request = lambda: None  # noqa: E731
            request.device = lambda: None
            request.device.dev_eui = deviceReq.dev_eui
            request.device.name = f"device_name{dev_no}"
            request.device.device_profile_id = f"device_profile_id{dev_no}"
            request.device.is_disabled = get_size("disabled")
            if getdevcount[0] <= 1:
                request.last_seen_at = ""
            else:
                request.last_seen_at = lambda: None
                t_stamp = math.modf(time.time() - (getdevcount[0] % 2) - 0.5)
                request.last_seen_at.seconds = int(t_stamp[1])
                request.last_seen_at.nanos = int(t_stamp[0] * 1e9)
            getdevcount[0] += 1
            return request

        def Create(self, deviceReq, metadata):
            """Get mocked device create request response."""
            return lambda: None

    @staticmethod
    def ListDevicesRequest():
        """Get list devices request object, only properties used in test are initialized."""
        request = lambda: None  # noqa: E731
        request.limit = None
        request.application_id = None
        return request

    @staticmethod
    def GetDeviceRequest(dev_eui=None):
        """Get device request object, only properties used in test are initialized."""
        request = lambda: None  # noqa: E731
        request.dev_eui = dev_eui
        return request

    class DeviceProfileServiceStub:
        """Device profile service implementation."""

        def __init__(self, channel) -> None:
            """Device profile service initialization implementation."""

        def List(self, listDeviceProfileReq, metadata):
            """Get response list object for device profile request."""
            no_of_devices = get_size("devices")
            request = lambda: None  # noqa: E731
            if listDeviceProfileReq.limit is not None:
                request.result = []
                for i in range(no_of_devices):
                    device = lambda: None  # noqa: E731
                    device.dev_eui = f"dev_eui{i}"
                    device.name = f"profile_name{i}"
                    device.device_profile_id = f"device_profile_id{i}"
                    device.device_status = lambda: None
                    device.device_status.battery_level = 95
                    device.device_status.external_power_source = (i % 2) == 0
                    request.result.append(device)
            request.total_count = no_of_devices
            return request

        def Get(self, deviceProfileReq, metadata):
            """Get response object for device profile request."""
            dev_no = int(deviceProfileReq.id[17:])
            request = lambda: None  # noqa: E731
            request.device_profile = lambda: None
            request.device_profile.id = deviceProfileReq.id
            request.device_profile.uplink_interval = 1
            request.device_profile.device_status_req_interval = 71

            request.device_profile.measurements = {}
            if get_size("codec") < 0:
                request.device_profile.payload_codec_script = ""
            elif get_size("codec") == 0:
                request.device_profile.payload_codec_script = CODEC[get_size("codec")][
                    1
                ].replace("{dev_no}", str(dev_no))
                measurement = lambda: None  # noqa: E731
                measurement.name = f"sensor{dev_no}"
                request.device_profile.measurements[measurement.name] = measurement
            else:
                request.device_profile.payload_codec_script = CODEC[get_size("codec")][
                    1
                ]
            request.device_profile.name = f"profile_name{dev_no}"
            request.device_profile.description = "Man_" + request.device_profile.name
            request.device_profile.mac_version = 0
            if "zeroentityvalues" in request.device_profile.payload_codec_script:
                measurement = lambda: None  # noqa: E731
                measurement.name = "s0"
                request.device_profile.measurements["s0"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "s1"
                request.device_profile.measurements["s1"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "l0"
                request.device_profile.measurements["l0"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "l1"
                request.device_profile.measurements["l1"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "i0"
                request.device_profile.measurements["i0"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "i1"
                request.device_profile.measurements["i1"] = measurement
            else:
                measurement = lambda: None  # noqa: E731
                measurement.name = "counter"
                request.device_profile.measurements["counter"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "battery"
                request.device_profile.measurements["battery"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "battery_voltage"
                request.device_profile.measurements["battery_voltage"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "rssi"
                request.device_profile.measurements["rssi"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "state"
                request.device_profile.measurements["state"] = measurement
                measurement = lambda: None  # noqa: E731
                measurement.name = "altitude"
                request.device_profile.measurements["altitude"] = measurement
            request.device_profile.DESCRIPTOR = lambda: None
            request.device_profile.DESCRIPTOR.fields_by_name = {}
            mac_version = lambda: None  # noqa: E731
            mac_version.enum_type = lambda: None
            mac = lambda: None  # noqa: E731
            mac.name = "11"
            mac_version.enum_type.values_by_number = [mac]
            request.device_profile.DESCRIPTOR.fields_by_name["mac_version"] = (
                mac_version
            )
            return request

        def Update(self, deviceProfileReq, metadata):
            """Get response object for device profile update request."""
            return lambda: None

    @staticmethod
    def GetDeviceProfileRequest(id=None):
        """Prepare device profile request object, only properties needd for test created."""
        request = lambda: None  # noqa: E731
        request.id = id
        request.limit = None
        return request

    @staticmethod
    def UpdateDeviceProfileRequest(device_profile):
        """Prepare device profile update request object, only properties needd for test created."""
        return lambda: None

    class GatewayServiceStub:
        """Gateway service implementation."""

        def __init__(self, channel) -> None:
            """Gateway service initialization implementation."""

        def List(self, listDevicesReq, metadata=None):
            """Get mocked list gateway request response."""
            no_of_gateways = get_size("gateways")
            request = lambda: None  # noqa: E731
            request.result = None
            if listDevicesReq.limit is not None:
                request.result = []
                for i in range(no_of_gateways):
                    gateway = lambda: None  # noqa: E731
                    gateway.dev_eui = f"dev_eui{i}"
                    gateway.gateway_id = "gatewayId0"  # f"gatewayId{i}"
                    gateway.name = gateway.gateway_id
                    gateway.tenant_id = f"TenantId{i}"
                    request.result.append(gateway)
            request.total_count = no_of_gateways
            return request

    @staticmethod
    def ListGatewaysRequest():
        """Get list devices request object, only properties used in test are initialized."""
        request = lambda: None  # noqa: E731
        request.limit = None
        # request.application_id = None
        return request


class grpc:
    """grpc interface mock."""

    def insecure_channel(self):
        """Return Channel mock."""
        return grpc.Channel(None, None, None, None)

    class Channel:
        """Channel mock."""

        def __init__(
            self,
            target: str,
            options: None,
            credentials: None,
            compression: None,
        ) -> None:
            """Prepare channel for test, raise exception if requested."""
            if not get_size("grpc"):
                raise Exception("Could not connect to grpc server")  # pylint: disable=broad-exception-raised  # noqa: TRY002

        def unary_unary(self, api, request_serializer=None, response_deserializer=None):
            """unary_unary for channel mock."""

        def close(self):
            """Close channel - dummy for mock."""


class dukpy:
    """dukpy class mock."""

    def __init__(self) -> None:
        """Dukpy class init mock."""

    class JSInterpreter:
        """JSInterpreter class mock."""

        def evaljs(self, code, **kwargs):
            """JSInterpreter evaljs mock."""
            return "{aaa+}"
