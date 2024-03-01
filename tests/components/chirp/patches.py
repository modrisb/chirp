"""Mocks for ChirpStack grpc api, paho mqtt."""
import json

MODEL_SIZES = [
    {
        "tenants": 2,
        "applications": 1,
        "devices": 2,
        "mqtt": 1,
        "grpc": 1,
        "publish": 1,
        "codec": 1,
    }
]
CODEC = [
    (
        4,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {sensor{dev_no}:{entity_conf: {device_class: "gas"}},battery:{entity_conf: {value_template: "{{ batteryLevel }}",entity_category: "diagnostic",device_class: "battery",unit_of_measurement: "%",}},rssi:{entity_conf: {value_template: "{{ value_json.rxInfo[-1].rssi | int }}",entity_category: "diagnostic",device_class: "signal_strength",}},altitude:{entity_conf:{value_template: "{{ value_json.rxInfo[-1].location.altitude | int }}"}}}};}',
    ),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {device_class: "gas"}}}};}',
    ),
    (
        2,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},rssi:{data_event: "status",entity_conf: {value_template: "{{ value_json.rxInfo[-1].rssi | int }}",entity_category: "diagnostic",device_class: "signal_strength",}}}};}',
    ),
    (0, "function getHaDeviceInfo() {return {device:"),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: \'model1\',},// \nentities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}}}};}',
    ),
    (
        2,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},battery:{data_event: "status",entity_conf: {value_template: "{{ value_json.batteryLevel}}",entity_category: "diagnostic",device_class: "battery",unit_of_measurement: "%",}}}};}',
    ),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},}}}};}',
    ),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{integration:"sensor",entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas",state_class: "total_increasing",unit_of_measurement: "m³"}},}}}};}',
    ),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",state_class: "total_increasing",unit_of_measurement: "m³"}},}}}};}',
    ),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas001",state_class: "total_increasing",unit_of_measurement: "m³"}},}}}};}',
    ),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "gas001",state_class: "total_increasing",command_topic:"{command_topic}",unit_of_measurement: "m³"}},}}}};}',
    ),
    (0, 'function getHaDeviceInf() {return {device:,""}}'),
    (0, 'function getHaDeviceInfo() {retur {device:,""}}'),
    (0, "function getHaDeviceInfo() {return "),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: \'model1\',},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: / \n"gas",state_class: "total_increasing",unit_of_measurement: "m³"}}}};}',
    ),
    (
        1,
        'function getHaDeviceInfo() {return {device: {manufacturer: "vendor0",model: "model1",},entities: {counter:{entity_conf: {value_template: "{{ value_json.object.counter }}",device_class: "humidifier",state_class: "total_increasing",unit_of_measurement: "m³"}},}}}};}',
    ),
    (
        1,
        "function getHaDeviceInfo() {return {device: {manufacturer: 'vendor0',model: '\"model1',},entities: {counter:{entity_conf: {value_template: '{{ value_json.object.counter }}'}},}}}};}",
    ),
]


def get_size(type_name):
    """Get test mock parameters."""
    if type_name == "sensors":
        return CODEC[get_size("codec")][0]
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


class message:
    """Class to represent mqtt message."""

    def __init__(self, topic, payload, qos=0, retain=False) -> None:
        """Initialize message, ensure payload encoding."""
        self.topic = topic
        if payload and hasattr(payload, "encode"):
            self.payload = payload.encode()
        else:
            self.payload = payload
        self.qos = qos
        self.retain = retain


class mqtt:
    """Mock paho mqtt interface."""

    class Client:
        """Mock paho mqtt Client class."""

        _publish_count = 0
        _published = []
        _subscribed = set()
        on_message = None
        on_publish = None
        _stat_start_time = 0
        _stat_dev_eui = None
        stat_devices = 0
        stat_sensors = 0

        def __new__(cls):
            """Implement singleton for test."""
            if not hasattr(cls, "instance"):
                cls.instance = super(mqtt.Client, cls).__new__(cls)
            return cls.instance

        def username_pw_set(self, user, pwd):
            """Mock username_pw_set function."""

        def connect(self, host, port):
            """Mock connect function, raise exception if requested."""
            if not get_size("mqtt"):
                raise Exception("Could not connect to mqtt server") # pylint: disable=broad-exception-raised
            return 0

        def publish(self, topic, payload, qos=0, retain=True):
            """Mock publish function, raise exception if requested."""
            self._publish_count += 1
            if not get_size("publish"):
                raise Exception("processing error") # pylint: disable=broad-exception-raised
            self._published.append((topic, payload, qos, retain))
            sub_topics = topic.split("/")
            if payload and sub_topics[-1] in self._subscribed:
                self.on_message(self, None, message(topic, payload, qos, retain))
            if sub_topics[-1] == "config" and len(sub_topics[2]) < 32:
                payload_struct = (
                    json.loads(payload) if payload and len(payload) > 0 else None
                )
                if payload_struct:
                    if self._stat_start_time != payload_struct["time_stamp"]:
                        self._stat_start_time = payload_struct["time_stamp"]
                        self.stat_devices = 0
                        self.stat_sensors = 0
                        self._stat_dev_eui = None
                    self.stat_sensors += 1
                    if self._stat_dev_eui != sub_topics[2]:
                        self._stat_dev_eui = sub_topics[2]
                        self.stat_devices += 1
            return (0, self._publish_count)

        def loop_start(self):
            """Mock loop_start function."""
            return 0

        def subscribe(self, topic):
            """Mock subscribe function."""
            sub_topics = topic.split("/")
            self._subscribed.add(sub_topics[-1])
            return (0, 0)

        def unsubscribe(self, topic):
            """Mock unsubscribe function."""
            return (0, 0)

        def loop_stop(self):
            """Mock loop_stop function."""
            return 0

        def disconnect(self):
            """Mock disconnect function."""
            return 0

        # for testing only
        def get_published(self):
            """Implement published message retrieval and buffer cleanup."""
            current = self._published
            self._published = []
            return current

        def reset_stats(self):
            """Reset device/sensor counters."""
            self._stat_start_time = None
            self.stat_devices = 0
            self.stat_sensors = 0
            self._stat_dev_eui = None


class api:
    """ChirpStack api mock implementation."""

    def TenantServiceStub(self):
        """Get tenant service object."""
        return api.TenantService()

    class TenantService:
        """Tenant service class mock."""

        def List(self, listTenantsReq, metadata):
            """Get mocked list tenants request response."""
            no_of_tenants = get_size("tenants")
            request = lambda: None
            if listTenantsReq.limit is not None:
                request.result = []
                for i in range(0, no_of_tenants):
                    tenant = lambda: None
                    tenant.name = f"TenantName{i}"
                    tenant.id = f"TenantId{i}"
                    request.result.append(tenant)
            request.total_count = no_of_tenants
            return request

    def ListTenantsRequest():
        """Prepare list tenants request object, initialize only used in test fields."""
        request = lambda: None
        request.limit = None
        return request

    def ApplicationServiceStub(self):
        """Get application service object."""
        return api.ApplicationService()

    class ApplicationService:
        """Application service class mock."""

        def List(self, listApplicationsReq, metadata):
            """Get mocked applications list request response."""
            no_of_applications = get_size("applications")
            request = lambda: None
            if listApplicationsReq.limit is not None:
                request.result = []
                for i in range(0, no_of_applications):
                    appl = lambda: None
                    appl.name = f"ApplicationName{i}"
                    appl.id = f"ApplicationId{i}"
                    request.result.append(appl)
            request.total_count = no_of_applications
            return request

    def ListApplicationsRequest():
        """List applications request object."""
        request = lambda: None
        request.limit = None
        return request

    def DeviceServiceStub(self):
        """Get device service object."""
        return api.DeviceService()

    class DeviceService:
        """Device service class mock."""

        def List(self, listDevicesReq, metadata):
            """Get mocked list devices request response."""
            no_of_devices = get_size("devices")
            request = lambda: None
            if listDevicesReq.limit is not None:
                request.result = []
                for i in range(0, no_of_devices):
                    device = lambda: None
                    device.dev_eui = f"dev_eui{i}"
                    device.name = f"device_name{i}"
                    device.device_profile_id = f"device_profile_id{i}"
                    device.device_status = lambda: None
                    device.device_status.battery_level = 95
                    device.device_status.external_power_source = (i % 2) == 1
                    request.result.append(device)
            request.total_count = no_of_devices
            return request

        def Get(self, deviceReq, metadata):
            """Get mocked device request response."""
            dev_no = int(deviceReq.dev_eui[7:])
            request = lambda: None
            request.device = lambda: None
            request.device.dev_eui = deviceReq.dev_eui
            request.device.name = f"device_name{dev_no}"
            request.device_profile_id = f"device_profile_id{dev_no}"
            request.device.is_disabled = get_size("disabled")
            return request

    def ListDevicesRequest():
        """Get list devices request object, only properties used in test are initialized."""
        request = lambda: None
        request.limit = None
        request.application_id = None
        return request

    def GetDeviceRequest():
        """Get device request object, only properties used in test are initialized."""
        request = lambda: None
        request.dev_eui = None
        return request

    def DeviceProfileServiceStub(self):
        """Get device profile service object."""
        return api.DeviceProfileService()

    class DeviceProfileService:
        """Device profile service class mock."""

        def List(self, listDeviceProfileReq, metadata):
            """Get response list object for device profile request."""
            no_of_devices = get_size("devices")
            request = lambda: None
            if listDeviceProfileReq.limit is not None:
                request.result = []
                for i in range(0, no_of_devices):
                    device = lambda: None
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
            request = lambda: None
            request.device_profile = lambda: None
            request.device_profile.id = deviceProfileReq.id
            request.device_profile.measurements = {}
            if get_size("codec") < 0:
                request.device_profile.payload_codec_script = ""
            elif get_size("codec") == 0:
                request.device_profile.payload_codec_script = CODEC[get_size("codec")][
                    1
                ].replace("{dev_no}", str(dev_no))
                measurement = lambda: None
                measurement.name = f"sensor{dev_no}"
                request.device_profile.measurements[measurement.name] = measurement
            else:
                request.device_profile.payload_codec_script = CODEC[get_size("codec")][
                    1
                ]
            request.device_profile.name = f"profile_name{dev_no}"
            request.device_profile.mac_version = 0
            measurement = lambda: None
            measurement.name = "counter"
            request.device_profile.measurements["counter"] = measurement
            measurement = lambda: None
            measurement.name = "battery"
            request.device_profile.measurements["battery"] = measurement
            measurement = lambda: None
            measurement.name = "rssi"
            request.device_profile.measurements["rssi"] = measurement
            measurement = lambda: None
            measurement.name = "state"
            request.device_profile.measurements["state"] = measurement
            measurement = lambda: None
            measurement.name = "altitude"
            request.device_profile.measurements["altitude"] = measurement
            request.device_profile.DESCRIPTOR = lambda: None
            request.device_profile.DESCRIPTOR.fields_by_name = {}
            mac_version = lambda: None
            mac_version.enum_type = lambda: None
            mac = lambda: None
            mac.name = "11"
            mac_version.enum_type.values_by_number = [mac]
            request.device_profile.DESCRIPTOR.fields_by_name[
                "mac_version"
            ] = mac_version
            return request

    def GetDeviceProfileRequest():
        """Prepare device profile request object, only properties needd for test created."""
        request = lambda: None
        request.id = None
        request.limit = None
        return request


class grpc:
    """grpc interface mock."""

    def insecure_channel(self):
        """Return Channel mock."""
        return grpc.Channel()

    class Channel:
        """Channel mock."""

        def __init__(self) -> None:
            """Prepare channel for test, raise exception if requested."""
            if not get_size("grpc"):
                raise Exception("Could not connect to grpc server") # pylint: disable=broad-exception-raised

        def close(self):
            """Close channel - dummy for mock."""
