# Motor Controller Skill

## Description
Controls DC motors via H-bridge drivers (like L298N). Supports forward, reverse, and stop movements with PWM speed control.

## Hardware Configuration
- **Type**: DC Motors with L298N Driver
- **Controllers**: 4 independent motor channels.
- **Pins (Arduino Mega)**:
  - `MOT_1`: IN1: 25, IN2: 26, EN: 27
  - `MOT_2`: IN1: 28, IN2: 29, EN: 30
  - `MOT_3`: IN1: 31, IN2: 32, EN: 33
  - `MOT_4`: IN1: 34, IN2: 35, EN: 36
- **Features**: Speed control via PWM (EN pins).

## Communication Protocol
**Base ID**: `MOT`
**Specific IDs**: `MOT_1`, `MOT_2`, `MOT_3`, `MOT_4`

### Commands (Incoming)
Format: `MOT:{SPECIFIC_ID}:{DIRECTION},[SPEED]`

| Direction | Speed | Description | Example |
|-----------|-------|-------------|---------|
| `FWD` | `0-255` | Move forward at `<speed>`. | `MOT:MOT_1:FWD,200` |
| `REV` | `0-255` | Move backward at `<speed>`. | `MOT:MOT_1:REV,150` |
| `STOP` | N/A | Stop the motor. | `MOT:MOT_1:STOP` |
| `<dir>` | N/A | Direction only, speed defaults to `0`. | `MOT:MOT_1:FWD` |

### Responses (Outgoing)
Format: `{SPECIFIC_ID}:{MSG}`

| Message | Description |
|---------|-------------|
| `DIR:FWD,SPD:<speed>` | Moving forward at `<speed>`. |
| `DIR:REV,SPD:<speed>` | Moving reverse at `<speed>`. |
| `STATE:STOP` | Motor stopped. |

## Implementation Details
- Uses high/low digital outputs for direction (IN1/IN2) and PWM for speed (EN).
- **Note**: Current `MotorController` implementation expects the specific ID to be part of the direction string if not careful (Bug check: `parseMessage` doesn't currently strip `targetId` from the command string before processing).
