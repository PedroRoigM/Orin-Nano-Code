# LED Controller Skill

## Description
Controls WS2812B NeoPixel LED strips. Supports state changes, color settings, brightness adjustment, and simple animations.

## Hardware Configuration
- **Type**: WS2812B NeoPixel Strip
- **Pins**: 
  - `LED_1`: Pin 22 (Arduino Mega)
  - `LED_2`: Pin 23 (Arduino Mega)
- **Pixels**: 200 per strip (default)
- **Library**: Adafruit_NeoPixel

## Communication Protocol
**Base ID**: `LED`
**Specific IDs**: `LED_1`, `LED_2`

### Commands (Incoming)
Format: `LED:{SPECIFIC_ID}:{COMMAND}`

| Command | Description | Example |
|---------|-------------|---------|
| `ON` | Turns all pixels on with current color and brightness. | `LED:LED_1:ON` |
| `OFF` | Turns all pixels off. | `LED:LED_1:OFF` |
| `COLOR:r,g,b` | Sets the color and turns pixels on. (0-255) | `LED:LED_1:COLOR:255,0,0` |
| `RANDOM` | Sets a random color and turns pixels on. | `LED:LED_1:RANDOM` |
| `BLINK` | Plays a sequential blink animation across all pixels. | `LED:LED_1:BLINK` |
| `BRIGHTNESS:val` | Adjusts brightness (0-255). | `LED:LED_1:BRIGHTNESS:128` |

### Responses (Outgoing)
Format: `{SPECIFIC_ID}:{PREFIX}:{VALUE}`

| Prefix | Value | Description |
|--------|-------|-------------|
| `STATE` | `ON`/`OFF` | Confirmation of state change. |
| `COLOR` | `r,g,b` | Confirmation of new color. |
| `BRIGHTNESS` | `val` | Confirmation of new brightness. |

## Implementation Details
- Default color: White (255, 255, 255)
- Default brightness: 50
- Uses non-blocking `Update` method via the Coordinator/Observer pattern.
