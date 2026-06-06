"""Constants for Alexa Appliances."""

import logging

DOMAIN = "alexa_appliances"
_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL_SECONDS = 60

GQL_SMART_HOME_QUERY = """
query CustomerSmartHome {
    endpoints(
      endpointsQueryParams: { paginationParams: { disablePagination: true } }
    ) {
        items {
            legacyAppliance {
                applianceId
                applianceTypes
                friendlyName
                friendlyDescription
                manufacturerName
                connectedVia
                modelName
                entityId
                capabilities
                customerDefinedDeviceType
                driverIdentity
            }
        }
    }
}
"""

ALEXA_DEVICES_DOMAIN = "alexa_devices"

ECHO_APPLIANCE_TYPES = {"ALEXA_VOICE_ENABLED", "ECHO", "TABLET"}

USER_AGENT = "AmazonWebView/AmazonAlexa/2.2.663733.0/iOS/18.5/iPhone"
