# Alexa Appliances

A Home Assistant custom integration that exposes Alexa-connected smart home appliances (dishwashers, ovens, washing machines, etc.) as native HA entities.

The official [Alexa Devices](https://www.home-assistant.io/integrations/alexa_devices/) integration only discovers Echo/Fire TV devices. This integration uses the same Alexa API session to discover and control **all other** smart home devices registered in your Alexa account — the ones you'd normally only control through the Alexa app.

## Requirements

- **Home Assistant 2025.6+**
- **Alexa Devices** core integration configured and authenticated — this integration reads the existing session cookies from it. No separate login required.

## Installation

### HACS (recommended)

1. Add this repository as a custom repository in HACS
2. Search for "Alexa Appliances" and install
3. Restart Home Assistant
4. Go to Settings → Devices & Services → Add Integration → Alexa Appliances

### Manual

Copy `custom_components/alexa_appliances` to your `config/custom_components/` directory and restart.

## How It Works

This integration calls the same undocumented Alexa Smart Home API that the Alexa mobile app uses:

- **Discovery**: A GraphQL query to `/nexus/v1/graphql` returns all smart home devices, not just Echo hardware
- **State polling**: `POST /api/phoenix/state` reads the current state of each appliance
- **Control**: `PUT /api/phoenix/state` sends commands (turn on/off, set mode, toggle options)

Authentication is handled entirely by the official `alexa_devices` integration — this integration reads the stored session cookies from its config entry.

## Supported Capabilities

Alexa capabilities are mapped to HA entity types:

| Alexa Capability | HA Platform | Examples |
|---|---|---|
| `PowerController` | Switch | Power on/off |
| `ToggleController` | Switch | Hi Temp Wash, Sanitize, Child Lock, Pause |
| `ModeController` (writable) | Select | Wash Cycle, Wash Zone |
| `ModeController` (read-only) | Sensor | Current Status, Remaining Time |
| `RangeController` | Number | Delay Start |
| `EndpointHealth` | Sensor | Connectivity |

Any Alexa-connected appliance that exposes these capabilities should work, not just dishwashers.

## Example: Sharp Dishwasher (SDW6767HS)

Entities created:

**Controls (Switch/Select/Number):**
- Power, Pause, Hi Temp Wash, Heat Dry, Fan Dry, Sanitize, Power Wash, Child Lock
- Wash Cycle (Auto, Heavy Duty, Normal, Light, Express Wash, Rinse Only)
- Wash Zone (Upper, Lower, Both)
- Delay Start (0-24 hours)

**Sensors:**
- Current Status (Off, Washing, Drying, Done, Error, etc.)
- Remaining Time
- Rinse Aid Status
- Connectivity

## Limitations

- **Cloud-only**: All communication goes through Amazon's servers. No local control.
- **Polling**: State is polled every 60 seconds. No push updates.
- **Undocumented API**: Amazon could change or break these endpoints at any time.
- **Session dependency**: If your `alexa_devices` session expires, this integration will also stop working until you re-authenticate.

## License

MIT
