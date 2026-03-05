---
name: Arduino Observer Pattern
description: Context simplification for the observer pattern implemented in the ArduinoBoardFirmware project.
---

# Arduino Observer Pattern Skill

This skill provides context about the custom observer pattern implementation used in the ArduinoBoardFirmware.

## Architecture Overview

The system uses a classic Observer pattern adapted for Arduino's constrained memory and compilation behavior.

### Classes

1.  **`IObserver` (Interface)**: Defined in `ObserverPatternDelcaration.h`. Base interface for all observers.
2.  **`ISubject` (Interface)**: Defined in `ObserverPatternDelcaration.h`. Base interface for subjects (Coordinator).
3.  **`GeneralController`**: Defined in `GeneralController.h/.ino`. Base class for hardware controllers, inherits `IObserver`.
4.  **`Coordinator`**: Defined in `Coordinator.h/.ino`. The central hub (Subject) that routes Serial messages to specific controller groups.
5.  **Concrete Controllers**: `LedController`, `LcdController`, `BuzzerController`, `MotorController`, `UltrasoundController`.

## Memory Optimization

- No dynamic memory allocation (`malloc`/`new`) is used for the observer lists.
- Instead, the `Vector` library is used with pre-allocated static buffers defined by `MAX_*_OBSERVERS` constants in `ObserverPatternDelcaration.h`.

## Compilation Model (Crucial)

To avoid "incomplete type" or "multiple definition" errors in the Arduino IDE:
- **Declarations** live in `.h` files.
- **Implementations** live in `.ino` files (using out-of-line syntax like `void ClassName::method()`).
- All `.h` files are included via `ControllerDeclaration.h`, which is included in the main `ArduinoBoardFirmware.ino`.

## Serial Protocol

Messages follow the format: `TYPE:PAYLOAD\n`
- `TYPE`: `LED`, `LCD`, `BUZZ`, `MOT`, `US`.
- `PAYLOAD`: Command string specific to the controller (e.g., `ON`, `OFF`, `PING`, speed values).

## Sanity Tests

Every controller implements a `sanityTest()` method called during `setup()` to verify hardware functionality at boot.
