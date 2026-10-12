<img src="custom_components/voltronic_udp/brand/icon.png" width="96" alt="Voltronic UDP Inverter icon">

# Voltronic UDP Inverter

Native Home Assistant custom integration for Voltronic-compatible Wi-Fi inverter bridges that expose the PIP protocol over UDP (normally port 1025).
Tested on the 2E-SM-4k224t inverter.

## Install with HACS

1. In HACS, open **Integrations** → the three-dot menu → **Custom repositories**.
2. Add the [https://github.com/sergkh/ha-voltronic-udp](https://github.com/sergkh/ha-voltronic-udp) repository and select **Integration**.
3. Install **Voltronic UDP Inverter**, restart Home Assistant, then go to **Settings → Devices & services → Add integration**.
4. Enter the inverter IP address. Destination and source ports default to `1025` and can be changed in the setup form. The polling interval defaults to 10 seconds (allowed range: 5–3600 seconds) and can later be changed from the integration's **Configure** menu; Home Assistant reloads the integration automatically.

For manual installation, copy `custom_components/voltronic_udp` to `/config/custom_components/voltronic_udp`, restart Home Assistant, and add it from **Devices & services**.

## Protocol scope

Only read-only PIP commands are sent: `QMN`, `QPIGS`, and `QMOD`. A transient `NAK` response is retried.

The inverter's compact `QMOD` protocol codes are shown as readable operating
states: **Power on**, **Standby**, **Line mode**, **Battery mode**, **Fault**,
or **Power saving**. The original one-letter protocol code remains available as
the entity's `protocol_mode` attribute for diagnostics.

PV input power is calculated locally as reported PV input voltage multiplied by
reported PV input current. It is DC input power at the inverter, not an energy
meter and not an allowance for conversion losses.

PV input energy is a persistent, locally integrated counter derived from that
power. It uses `energy` / `kWh` / `total_increasing`, so it is suitable for the
Energy dashboard's solar-production source. It begins accumulating only after
the integration is running and does not estimate energy during outages.
