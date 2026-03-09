# Buzzer Controller Skill

## Description
Controls auditory feedback using piezo buzzers. Supports generating specific frequencies for defined durations and immediate silence.

## Hardware Configuration
- **Type**: Passive/Active Piezo Buzzer
- **Pins**:
  - `BUZZ_1`: Pin 7 (Arduino Mega)
  - `BUZZ_2`: Pin 6 (Arduino Mega)
- **Features**: Uses `tone()` and `noTone()` Arduino functions.

## Communication Protocol
**Base ID**: `BUZZ`
**Specific IDs**: `BUZZ_1`, `BUZZ_2`

### Commands (Incoming)
Format: `BUZZ:{SPECIFIC_ID}:{COMMAND}`

| Command | Description | Example |
|---------|-------------|---------|
| `OFF` | Stops any sound currently playing on the buzzer. | `BUZZ:BUZZ_1:OFF` |
| `SOUND:<freq>,<duration>` | Plays a tone at `<freq>` Hz for `<duration>` ms. | `BUZZ:BUZZ_1:SOUND:1000,500` |

### Responses (Outgoing)
Format: `{SPECIFIC_ID}:{PREFIX}:{VALUE}`

| Prefix | Value | Description |
|--------|-------|-------------|
| `STATE` | `OFF` | Confirmation of silence. |
| `TONE` | `<freq>,<duration>` | Confirmation of tone played. |

## Implementation Details
- Uses non-blocking `Update` via the Coordinator, though `tone()` itself is semi-blocking or background depending on implementation.
- Parameters must be valid integers; invalid or zero values are ignored.
