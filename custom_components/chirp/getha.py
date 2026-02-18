UPLINK_FUNCTION_NAME = "decodeUplink"
DATA_PROPERTY_NAME = "data"
ARRAY_FUNCS = ["push", "pull", "shift", "pop"]
PROPERTIES_TO_IGNORE = ["errors", "warnings"]
DEFAULT_MANUFACTURER = "Unknown manufacturer"
HA_HEAD = """
// auto generated HA integration function
function getHaDeviceInfo() {
    return {
        device: {
            manufacturer: "${manufacturer}",
            model: "${model}",
        },
        entities: {
"""
HA_BATTERY = """            battery_voltage:{
                entity_conf: {
                    value_template: "{{ value_json.object.battery_voltage | float }}",
                    entity_category: "diagnostic",
                    device_class: "voltage",
                    unit_of_measurement: "V"
                }
            },
"""
HA_SENSOR = """            ${sensor_name}:{
                //integration: "sensor",
                entity_conf: {
                    value_template: "{{ value_json.object.${sensor} }}",
                    //entity_category: "diagnostic",
                    //device_class: "voltage",
                    //unit_of_measurement: "V"
                }
            },
"""
HA_TAIL = """            rssi:{
                entity_conf: {
                    value_template: "{{ value_json.rxInfo[-1].rssi | int }}",
                    entity_category: "diagnostic",
                    device_class: "signal_strength",
                    unit_of_measurement: "dBm",
                }
            }
        }
    };
}
"""

import time
import logging

_LOGGER = logging.getLogger(__name__)


def generate_getHaDeviceInfo(codec, manufacturer, device, hasBaterry):
    #sensors = getHAFromCodec(codec)
    sensors = []
    haBody = HA_HEAD.replace("${manufacturer}", manufacturer if manufacturer else DEFAULT_MANUFACTURER).replace("${model}", device)
    for sensor in sensors:
        haBody += HA_SENSOR.replace("${sensor_name}", sensor.replace('.', '_')).replace("${sensor}", sensor)
    if hasBaterry:
        haBody += HA_BATTERY
    haBody += HA_TAIL
    return haBody
