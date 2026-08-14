---
dusk: v1alpha1
namespace: stout
kind: repository
name: ha-alexa-appliances
title: Alexa Appliances
attributes:
  language: python
  visibility: public
  distribution: hacs
---

A Home Assistant custom integration, domain `alexa_appliances`, that exposes the smart home devices an Alexa account knows about but the core `alexa_devices` integration ignores: dishwashers, ovens, washing machines, anything that is not Echo or Fire TV hardware.
Alexa capabilities are mapped onto platforms, so `PowerController` and `ToggleController` become switches, a writable `ModeController` becomes a select, a read-only one becomes a sensor, and `RangeController` becomes a number.

Install it through HACS as a custom repository, or copy `custom_components/alexa_appliances/` into a config directory and restart.
It needs Home Assistant 2025.6 or newer, has no Python requirements, and holds no credentials of its own.
What it does need is the core `alexa_devices` integration already set up, which the manifest declares as a hard dependency.

## Authentication is entirely borrowed

`build_session_cookies` reads `login_data` out of the `alexa_devices` config entry and merges `website_cookies` with the `store_authentication_cookie` value under the name `session-token`, because `website_cookies` alone omits it.
That jar is the whole login.
A CSRF token is then taken from the jar if it is there, and otherwise bootstrapped by fetching `/api/language`, `/spa/index.html` and `/api/devices-v2/device?cached=false` with redirects unfollowed, so a dead session surfaces as a 302 rather than as an HTML login page parsed as success.
Reads work without a token and only control needs one, which is why the two failure modes are separated in the error text: 200 with no csrf cookie means Amazon moved the token, 302 or 401 means the session is dead.
When the session goes, the coordinator raises `ConfigEntryAuthFailed` and the reauth flow simply re-reads the cookies from `alexa_devices`, so recovery is re-authenticating that integration rather than this one.

## What breaks first

Everything past the cookie jar is undocumented surface with no compatibility promise.
In rough order of how load-bearing they are: the `CustomerSmartHome` GraphQL query against `/nexus/v1/graphql` and the `legacyAppliance` shape it returns, then `POST` and `PUT /api/phoenix/state`, then the CSRF bootstrap URLs, then the hardcoded iPhone Alexa app `User-Agent`, then the cookie names themselves.
A discovery that returns zero appliances against a session Amazon still accepts is the GraphQL query having moved, not an auth problem.

Two smaller traps.
Echo hardware is filtered out by `applianceTypes` and by the presence of `Alexa.DoNotDisturbController`, so a new Amazon device type appearing as an appliance is a miss in that filter rather than a discovery bug.
State is fetched in concurrent chunks of twenty because seventy-six entities in one request came close to the thirty second timeout.
The README says state is polled every sixty seconds; `DEFAULT_SCAN_INTERVAL` is 120, and the options flow allows 30 to 600.
