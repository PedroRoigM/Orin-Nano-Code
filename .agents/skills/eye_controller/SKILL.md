# Eye Controller Skill

## Description
Controls dual GC9A01 circular TFT displays to render expressive robotic eyes. Supports gaze movement, color changing, and multiple pupil shapes with smooth 60 FPS interpolation.

## Hardware Configuration
- **Type**: GC9A01 1.28" Circular TFT (240x240)
- **Pins (Arduino Mega Hardware SPI)**:
  - `MOSI`: 51
  - `SCK`: 52
  - `DC`: 47
  - `RST`: 46
  - `CS_RIGHT`: 48
  - `CS_LEFT`: 49 (Note: Usually shared or handled via specific logic)
- **Features**: Fast I/O using Port L registers, hardware SPI at 8MHz.

## Communication Protocol
**Base ID**: `EYE`
**Specific IDs**: `EYE_1`, `EYE_2`

### Commands (Incoming)
Format: `EYE:{SPECIFIC_ID}:{COMMAND}`

| Command | Description | Example |
|---------|-------------|---------|
| `gx,gy,r,g,b` | Sets gaze offset (-100 to 100) and iris color (0-255). | `EYE:EYE_1:30,-10,255,200,0` |
| `COLOR:r,g,b` | Updates iris color only. | `EYE:EYE_1:COLOR:0,255,0` |
| `SHAPE:type` | Sets pupil shape (`circle`, `star`, `smiley`, `x`). | `EYE:EYE_1:SHAPE:star` |

### Responses (Outgoing)
Format: `{SPECIFIC_ID}:{MSG}`

| Message | Description |
|---------|-------------|
| `READY:ok` | Initialized and ready. |
| `EYE:ok` | Command processed successfully. |

## Implementation Details
- **Interpolation**: Movements are smoothed using a `0.3` interpolation factor for fluid 60 FPS updates.
- **Rendering**: Optimized specialized drawing functions for circular iris, pupil shapes, and "cute" highlights.
- **Mirroring**: Supports mirroring gaze for matching eye movements (usually LEFT eye is mirrored).
- **Coordinate System**: Internal mapping from -100/100 to `MAX_GAZE` pixel offset.
