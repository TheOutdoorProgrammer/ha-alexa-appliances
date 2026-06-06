"""Constants for Alexa Appliances."""

DOMAIN = "alexa_appliances"

DEFAULT_SCAN_INTERVAL = 120

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

ALEXA_HARDWARE_TYPES = {"ALEXA_VOICE_ENABLED", "ECHO", "TABLET", "FIRE_TV", "SMARTSPEAKER", "HUB"}
ALEXA_HARDWARE_CAPABILITIES = {"Alexa.DoNotDisturbController"}

USER_AGENT = "AmazonWebView/AmazonAlexa/2.2.663733.0/iOS/18.5/iPhone"
