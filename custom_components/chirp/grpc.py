"""The ChirpStack LoRaWAN Integration - grpc interface to ChirpStack server."""
from __future__ import annotations

import json
import logging
import subprocess
import dukpy
import re

from chirpstack_api import api
import grpc

from .getha import generate_getHaDeviceInfo
from .const import CONF_API_PORT, CONF_API_SERVER, CONF_APPLICATION_ID, CHIRPSTACK_TENANT, CHIRPSTACK_APPLICATION, ERRMSG_CODEC_ERROR
from .const import ERRMSG_DEVICE_IGNORED, WARMSG_APPID_WRONG, CHIRPSTACK_API_KEY_NAME, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)

class ChirpGrpc:
    """Chirp2MQTT grpc interface support."""
    """ChirpStack api details @ https://github.com/chirpstack/chirpstac k/tree/master/api/proto/api"""

    def __init__(self, config, version) -> None:
        """Open connection to ChirpStack api server."""
        self._config = config
        self._version = version
        self._application_id = self._config.get(CONF_APPLICATION_ID)
        self._channel = grpc.insecure_channel(
            f"{self._config.get(CONF_API_SERVER)}:{self._config.get(CONF_API_PORT)}"
        )
        bearer = self._config.get(CONF_API_KEY)
        self._token_id = "external"
        if not bearer:
            token_message = subprocess.run(["chirpstack", "-c", "/etc/chirpstack", "create-api-key", "--name", CHIRPSTACK_API_KEY_NAME], capture_output=True, text=True).stdout
            self._token_id = token_message.split("id: ")[-1].split("\n")[0]
            bearer = token_message.split("token: ")[-1].rstrip("\n")
        self._auth_token = [("authorization", f"Bearer {bearer}")]
        _LOGGER.info(
            "gRPC channel opened for %s:%s, token id %s",
            self._config.get(CONF_API_SERVER),
            self._config.get(CONF_API_PORT),
            self._token_id,
        )
        if not self.is_valid_app_id( self._application_id ):
            tenants_on_chirp = self.get_chirp_tenants()
            if len(tenants_on_chirp) == 0:
                tenant = api.TenantServiceStub(self._channel)
                createTenantReq = api.CreateTenantRequest()
                createTenantReq.tenant.name = CHIRPSTACK_TENANT
                createTenantReq.tenant.can_have_gateways = True
                createTenantReq.tenant.max_gateway_count = 1
                tenantResp = tenant.Create(createTenantReq, metadata=self._auth_token)
                _LOGGER.info("Tenant '%s' (id %s) created", createTenantReq.tenant.name, tenantResp.id)
                tenants_on_chirp = self.get_chirp_tenants()
            for tenant, id in tenants_on_chirp.items():
                tenant_id = id
                break
            applications_on_chirp = self.get_tenant_applications(tenant_id)
            if len(applications_on_chirp) == 0:
                application = api.ApplicationServiceStub(self._channel)
                createApplicationReq = api.CreateApplicationRequest()
                createApplicationReq.application.name = CHIRPSTACK_APPLICATION
                createApplicationReq.application.tenant_id = tenant_id
                applicationResp = application.Create(createApplicationReq, metadata=self._auth_token)
                _LOGGER.info("Application '%s' (id %s, tenant %s) created", createApplicationReq.application.name, tenant, applicationResp.id)
                applications_on_chirp = self.get_tenant_applications(tenant_id)
            for application, id in applications_on_chirp.items():
                application_id = id
                break
            _LOGGER.warning(WARMSG_APPID_WRONG, self._application_id, application_id, tenant, application)
            self._application_id = application_id
        self.js_interpreter = dukpy.JSInterpreter()
        _LOGGER.info("ChirpStack application ID %s", self._application_id)

    def get_chirp_tenants(self):
        """Get tenant list from api server, build name/id dictionary and return."""
        tenants = api.TenantServiceStub(self._channel)
        listTenantsReq = api.ListTenantsRequest()
        tenantsResp = tenants.List(listTenantsReq, metadata=self._auth_token)
        listTenantsReq.limit = tenantsResp.total_count
        tenantsResp = tenants.List(listTenantsReq, metadata=self._auth_token)
        return {tenant.name: tenant.id for tenant in tenantsResp.result}

    def get_tenant_applications(self, tenant_id):
        """Get applications list from api server, build name/id dictionary and return."""
        applications = api.ApplicationServiceStub(self._channel)
        listApplicationsReq = api.ListApplicationsRequest()
        listApplicationsReq.tenant_id = tenant_id
        applicationsResp = applications.List(
            listApplicationsReq, metadata=self._auth_token
        )
        listApplicationsReq.limit = applicationsResp.total_count
        applicationsResp = applications.List(
            listApplicationsReq, metadata=self._auth_token
        )
        return {
            application.name: application.id for application in applicationsResp.result
        }

    def is_valid_app_id(self, application_id):
        """Check application id validity with api server."""
        application = api.ApplicationServiceStub(self._channel)
        applicationReq = api.GetApplicationRequest()
        applicationReq.id = application_id
        try:
            application.Get( applicationReq, metadata=self._auth_token )
        except Exception:
            return False
        return True

    def get_chirp_app_devices(self):
        """Get application's devices from api server."""
        devices = api.DeviceServiceStub(self._channel)
        listDevicesReq = api.ListDevicesRequest()
        listDevicesReq.application_id = self._application_id
        devicesResp = devices.List(listDevicesReq, metadata=self._auth_token)
        listDevicesReq.limit = devicesResp.total_count
        devicesResp = devices.List(listDevicesReq, metadata=self._auth_token)
        return devicesResp.result

    #   [desc.name for desc, val in deviceReq.ListFields()]
    def get_chirp_device(self, dev_eui):
        """Get device details by dev_eui from api server."""
        device = api.DeviceServiceStub(self._channel)
        deviceReq = api.GetDeviceRequest()
        deviceReq.dev_eui = dev_eui
        device_details = device.Get(deviceReq, metadata=self._auth_token)
        return device_details

    def get_chirp_device_profile(self, device_profile_id):
        """Get device profile details by id from api server."""
        profile = api.DeviceProfileServiceStub(self._channel)
        listDevicesReq = api.GetDeviceProfileRequest()
        listDevicesReq.id = device_profile_id
        return profile.Get(listDevicesReq, metadata=self._auth_token)

    def update_chirp_device_profile(self, device_profile):
        """Update device profile."""
        profile = api.DeviceProfileServiceStub(self._channel)
        updateDevicesReq = api.UpdateDeviceProfileRequest(device_profile = device_profile)
        return profile.Update(updateDevicesReq, metadata=self._auth_token)

    def isDeviceDisbled(self, dev_eui):
        """Check if device with dev_eui is enabled by reading device details from api server."""
        device = self.get_chirp_device(dev_eui)
        return device.device.is_disabled

    def close(self):
        """Close grpc channel."""
        self._channel.close()

    def get_current_device_entities(self):
        """Get enabled device list from api server."""
        devices_list = []
        devices = self.get_chirp_app_devices()
        for device in devices:
            if self.isDeviceDisbled(device.dev_eui):
                continue
            profile = self.get_chirp_device_profile(device.device_profile_id)
            discovery = None
            codec_code = None
            codec_json = None
            try:
                mi_start = re.search(r"function\s+getHaDeviceInfo", profile.device_profile.payload_codec_script)
                if not mi_start:
                    _LOGGER.warning(
                        "Profile %s discovery codec script not found, generating one, will use manufacturer name '%s', device name '%s', baterry '%s'",
                        profile.device_profile.name,
                        profile.device_profile.description,
                        profile.device_profile.name,
                        not device.device_status.external_power_source
                    )
                    codec_code = generate_getHaDeviceInfo(profile.device_profile.payload_codec_script,
                                                          profile.device_profile.description,
                                                          profile.device_profile.name,
                                                          not device.device_status.external_power_source)
                    profile.device_profile.payload_codec_script += codec_code
                    self.update_chirp_device_profile(profile.device_profile)
                    mi_start = re.search(r"function\s+getHaDeviceInfo", profile.device_profile.payload_codec_script)
                if mi_start:
                    i_start = mi_start.start()
                    codec_code = profile.device_profile.payload_codec_script[i_start:]
                    discovery = self.js_interpreter.evaljs(codec_code+"; JSON.stringify(getHaDeviceInfo())")
                    codec_json = discovery
            except Exception as error:  # pylint: disable=broad-exception-caught
                _LOGGER.error(
                    ERRMSG_CODEC_ERROR,
                    profile.device_profile.name,
                    str(error),
                    codec_code,
                    codec_json,
                )
                discovery = None
            if discovery:
                try:
                    discovery = json.loads(discovery)
                except Exception as error:  # pylint: disable=broad-exception-caught
                    _LOGGER.debug(
                        "Profile %s discovery codec script error '%s', source code '%s' converted to json '%s'",
                        profile.device_profile.name,
                        str(error),
                        codec_code,
                        discovery,
                    )
                    discovery = None
            if not discovery:
                _LOGGER.error(
                    ERRMSG_DEVICE_IGNORED,
                    codec_code, codec_json,
                    device.name,
                    profile.device_profile.name,
                )
                continue
            for entity, config in discovery["entities"].items():
                discovery_config = config["entity_conf"]
                if not discovery_config.get("value_template"):
                    discovery_config[
                        "value_template"
                    ] = f"{{{{ value_json.object.{entity} }}}}"
                discovery_config["uplink_interval"] = profile.device_profile.uplink_interval

            mac_version = (
                profile.device_profile.DESCRIPTOR.fields_by_name["mac_version"]
                .enum_type.values_by_number[profile.device_profile.mac_version]
                .name
            )
            mac_version = (mac_version.replace("_", " ", 1)).replace("_", ".")
            discovery["dev_conf"] = {
                "last_seen": device.last_seen_at if str(device.last_seen_at) else None,
                "sw_version": mac_version,
                "dev_eui": device.dev_eui,
                "dev_name": device.name,
                "measurement_names": {
                    entity: profile.device_profile.measurements[entity].name
                    for entity in discovery["entities"]
                },
                "prev_value": {"batteryLevel": device.device_status.battery_level}
                if not device.device_status.external_power_source
                else {},
            }
            devices_list.append(discovery)
        return devices_list

    def get_device_visibility_info(self, dev_eui):
        """Get device visibility data from api server: device last seen time stamp and expected uplink interval."""
        device = self.get_chirp_device(dev_eui)
        profile = self.get_chirp_device_profile(device.device.device_profile_id)
        visibility = {}
        visibility["uplink_interval"] = profile.device_profile.uplink_interval
        visibility["device_status_req_interval"] = profile.device_profile.device_status_req_interval
        visibility["last_seen"] = device.last_seen_at.seconds+device.last_seen_at.nanos*1e-9 if str(device.last_seen_at) else 0
        return visibility
