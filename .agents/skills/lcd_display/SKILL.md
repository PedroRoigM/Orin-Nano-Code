# LCD Display Skill

## Description
Controls a 16x2 character LCD display via I2C. Displays text messages and provides status feedback.

## Hardware Configuration
- **Type**: 16x2 LCD with I2C Backpack (PCF8574T)
- **Pins (Arduino Mega)**:
  - `SDA`: 20
  - `SCL`: 21
- **I2C Address**: `0x27` (default)
- **Library**: `LiquidCrystal_I2C`

## Communication Protocol
**Base ID**: `LCD`
**Specific IDs**: `LCD_1` (usually only one)

### Commands (Incoming)
Format: `LCD:{SPECIFIC_ID}:{TEXT}`

| Command | Description | Example |
|---------|-------------|---------|
| `<any text>` | Displays the provided string on row 0 of the LCD. | `LCD:LCD_1:Hello World!` |

### Responses (Outgoing)
Format: `TEXT:{TEXT}`

| Prefix | Value | Description |
|--------|-------|-------------|
| `TEXT` | `<text>` | Confirmation of text displayed. |

## Implementation Details
- **Note**: The current `LcdController` implementation in `LcdController.ino` *does not* validate the `SPECIFIC_ID`. It will display any message received via the Coordinator's broadcast.
- Clears the display before printing new text.
- Sets cursor to `(0, 0)` automatically.
