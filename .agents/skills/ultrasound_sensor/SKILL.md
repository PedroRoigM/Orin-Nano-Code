# Ultrasound Sensor Skill

## Description
Measures distance using HC-SR04 ultrasonic sensors. Responds to trigger pulses and calculates distance based on echo timing.

## Hardware Configuration
- **Type**: HC-SR04 Ultrasound Sensor
- **Pins**:
  - `US_1`: TRIG: 38, ECHO: 39 (Arduino Mega)
  - `US_2`: TRIG: 40, ECHO: 41 (Arduino Mega)
- **Features**: 2 sensors for proximity detection.

## Communication Protocol
**Base ID**: `US`
**Specific IDs**: `US_1`, `US_2`

### Commands (Incoming)
Format: `US:{SPECIFIC_ID}:PING`

| Command | Description | Example |
|---------|-------------|---------|
| `PING` | Triggers a distance measurement. | `US:US_1:PING` |

### Responses (Outgoing)
Format: `{SPECIFIC_ID}:DIST:{VALUE}`

| Value | Description |
|-------|-------------|
| `<cm>` | Measured distance in centimeters. |
| `ERROR` | Measurement failed or timed out. |

## Implementation Details
- Uses `pulseIn()` with a 30ms timeout.
- Distance calculation: `duration / 58` for centimeters.
- Non-blocking `Update` via the Coordinator, but the sensor read itself has a small blocking delay (trigger pulse and echo wait).
