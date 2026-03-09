# System Coordinator Skill

## Description
The central orchestrator of the Arduino firmware. It manages the registration of controllers (observers) and routes serial messages to the appropriate components using a structured protocol.

## Architecture
- **Pattern**: Observer Pattern (Custom implementation)
- **Core Components**:
  - `Coordinator`: Receives and dispatches messages.
  - `IObserver`: Interface for all controllers.
  - `GeneralController`: Base class providing common functionality (ID management, Serial feedback).

## Serial Communication Protocol
All serial communication follows a colon-separated triple format:

**Inbound**: `{BASE_ID}:{SPECIFIC_ID}:{COMMAND}`
- `BASE_ID`: Component group (e.g., `LED`, `MOT`, `US`, `EYE`).
- `SPECIFIC_ID`: Unique instance identifier (e.g., `LED_1`, `MOT_3`).
- `COMMAND`: Component-specific instruction.

**Outbound**: `{SPECIFIC_ID}:{PREFIX}:{VALUE}` (Or simple confirmation)
- `SPECIFIC_ID`: Identity of the responding component.
- `PREFIX`: Type of feedback (e.g., `DIST`, `STATE`, `COLOR`).
- `VALUE`: Result or status.

## Routing Logic
1. `Coordinator::readAndRoute()` reads a newline-terminated string from `Serial`.
2. `parseMessage()` splits the string into three tokens.
3. `isValidMessage()` checks if the `BASE_ID` maps to a known list.
4. `dispatchCommand()` sends the message `{SPECIFIC_ID}:{COMMAND}` to all observers in the matching list.
5. Each observer's `Update()` method checks if `SPECIFIC_ID` matches its own `observerId`.

## Component Discovery
The Coordinator maintains lists for:
- LED strips
- LCD displays
- Buzzers
- Motors
- Ultrasound sensors
- GC9A01 Eyes

## Important Information
- **Baud Rate**: Defined in `ArduinoBoardFirmware.ino` (usually 115200 or 500000 for high-speed eyes).
- **Timeouts**: Serial reads use `readStringUntil('\n')`.
