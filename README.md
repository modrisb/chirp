# Chirp - ChirpStack LoraWan Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs) (https://github.com/modrisb/pijups/releases)


Chirp as [Home Assistant](https://home-assistant.io) integration component glues together HA MQTT and ChirStack LoraWan server. LoraWan devices information is retrived from ChirpStack gRPC api server and exposed to HA MQTT integration discovery service. Data transferred by/ty LoraWan devices are retained on MQTT server to support HA/integration restart. Detailed configuration information needed for HA is stored as ChirpStack codec extension.

## Sensors supported
* Chirp does not limit devices by type/features, but is limited by codec extension that need to be prepared for each device separately.

## Prerequisite
HA MQTT integration with MQTT server must be available to Chirp as to Chirpstack server also.<br>

## Manual installation 
1. Inside the `custom_components` directory, create a new folder called `chirp`.
2. Download all files from the `custom_components/chirp/` repository to this directory `custom_components/chirp`.
3. Install integration from Home Assistant Settings/Devices & Services/Add Integration and continue with UI configuration. ChirpStack server credentials required, including API key used for connection authentication. On HA side MQTT server credentials and MQTT discovery details needed.

HACS might be used for installation too - check repository 'Chirp'.

## Devices Configuration
Chirp uses ChirpStack device template information for device type details and device specifics (device enabled, device battery details), HA integration details are encoded in ChirpStack device template javascript codec. Codec must be appended by function similar to:

function getHaDeviceInfo() {
  return {
    device: {
      manufacturer: "Milesight IoT Co., Ltd",
      model: "WS52x"
    },
    entities: {
        current:{
        entity_conf: {
          value_template: "{{ (value_json.object.current | float) / 1000 }}",
          entity_category: "diagnostic",
          state_class: "measurement",
          device_class: "current",
          unit_of_measurement: "A"
        }
      },
        factor:{
        entity_conf: {
          value_template: "{{ (value_json.object.factor | float) / 100 }}",
          entity_category: "diagnostic",
          state_class: "measurement",
          device_class: "power_factor",
        }
      },
      power:{
        entity_conf: {
          value_template: "{{ value_json.object.power | float }}",
          entity_category: "diagnostic",
          state_class: "measurement",
          device_class: "power",
          unit_of_measurement: "W"
        }
      },
      voltage:{
        entity_conf: {
          value_template: "{{ value_json.object.voltage | float }}",
          entity_category: "diagnostic",
          state_class: "measurement",
          device_class: "voltage",
          unit_of_measurement: "V"
        }
      },
      outage:{
        integration: "binary_sensor",
        entity_conf: {
          entity_category: "diagnostic",
          device_class: "power"
        }
      },
      power_sum:{
        entity_conf: {
          value_template: "{{ (value_json.object.power_sum | float) / 1000 }}",
          state_class: "total_increasing",
          device_class: "energy",
          unit_of_measurement: "kWh"
        }
      },
      state:{
       integration: "switch",
       entity_conf: {
          value_template: "{{ value_json.object.state }}",
          command_topic: "{command_topic}",
          state_on: "open",
          state_off: "close",
          payload_off: '{{"dev_eui":"{dev_eui}","confirmed":true,"fPort":85,"data":"CAAA/w=="}}',
          payload_on: '{{"dev_eui":"{dev_eui}","confirmed":true,"fPort":85,"data":"CAEA/w=="}}'
        }
      },
      rssi:{
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

Device information is used only for visualization, entities describe sensor details - how they are integrated into HA. value_template defines sensor value extraction rules from device payload and possible conversions (like converting to int/float and applying needed factors). Integration type is needed for MQTT to implement proper processing together with device class definition.

## Add-on version
See https://github.com/modrisb/chirpha for add-on version of this integration.

## Credits
[ChirpStack](https://chirpstack.io/) : open-source LoRaWAN Network Server<br>
[Home Assistant](https://github.com/home-assistant) : Home Assistant open-source powerful domotic plateform with MQTT integratio.<br>
[HACS](https://hacs.xyz/) : Home Assistant Community Store gives you a powerful UI to handle downloads of all your custom needs.<br>
