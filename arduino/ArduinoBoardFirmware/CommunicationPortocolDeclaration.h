#ifndef COMMUNICATION_PORTOCOL_DECLARATION_H
#define COMMUNICATION_PORTOCOL_DECLARATION_H

// ---------------------------------------------------------------------------
// Protocol definition
//
// Expected message income
//   {BASE_COMPONENT_ID}:{SPECIFIC_COMPONENT_ID}:{COMMAND}
// Example:
//   US:US_1:PING
//
// Expected message outcome
//   {SPECIFIC_COMPONENT_ID}:{OUTPUT}
// Example:
//   US_1:DIST:10
//   US_1:DIST:ERROR
// ---------------------------------------------------------------------------

#define ERROR_MESSAGE "ERROR"

// ---------------------------------------------------------------------------
// LED
// ---------------------------------------------------------------------------
// Income:
//   LED:LED_<n>:ON
//   LED:LED_<n>:OFF
//   LED:LED_<n>:BLINK
//
// Outcome:
//   LED_<n>:STATE:ON
//   LED_<n>:STATE:OFF
//   LED_<n>:STATE:BLINK

#define LED_BASE_ID "LED"
#define LED_ID(num) LED_BASE_ID "_" #num
#define LED_CMD_ON "ON"
#define LED_CMD_OFF "OFF"
#define LED_CMD_BLINK "BLINK"
#define LED_CMD_COLOR "COLOR"
#define LED_CMD_RANDOM "RANDOM"
#define LED_STATE_PREFIX "STATE"
#define LED_COLOR_PREFIX "COLOR"
#define LED_BLINK_PREFIX "BLINK"
#define LED_BRIGHTNESS_PREFIX "BRIGHTNESS"

// ---------------------------------------------------------------------------
// LCD
// ---------------------------------------------------------------------------
// Income:
//   LCD:LCD_<n>:<text>         (any text string; displayed on row 0)
//
// Outcome:
//   LCD_<n>:TEXT:<text>

#define LCD_BASE_ID "LCD"
#define LCD_ID(num) LCD_BASE_ID "_" #num
#define LCD_TEXT_PREFIX "TEXT"

// ---------------------------------------------------------------------------
// Buzzer
// ---------------------------------------------------------------------------
// Income:
//   BUZZ:BUZZ_<n>:OFF
//   BUZZ:BUZZ_<n>:SOUND:<freq>,<duration_ms>   (e.g. "1000,500")
//
// Outcome:
//   BUZZ_<n>:STATE:OFF
//   BUZZ_<n>:TONE:<freq>,<duration_ms>

#define BUZZER_BASE_ID "BUZZ"
#define BUZZER_ID(num) BUZZER_BASE_ID "_" #num
#define BUZZER_CMD_OFF "OFF"
#define BUZZER_CMD_SOUND "SOUND"
#define BUZZER_STATE_PREFIX "STATE"
#define BUZZER_TONE_PREFIX "TONE"

// ---------------------------------------------------------------------------
// Motor
// ---------------------------------------------------------------------------
// Income:
//   MOT:MOT_<n>:FWD,<speed>   (<speed> 0-255)
//   MOT:MOT_<n>:REV,<speed>
//   MOT:MOT_<n>:STOP
//   MOT:MOT_<n>:<direction>    (direction only, speed defaults to 0)
//
// Outcome:
//   MOT_<n>:DIR:FWD,SPD:<speed>
//   MOT_<n>:DIR:REV,SPD:<speed>
//   MOT_<n>:STATE:STOP

#define MOTOR_BASE_ID "MOT"
#define MOTOR_ID(num) MOTOR_BASE_ID "_" #num
#define MOTOR_CMD_FWD "FWD"
#define MOTOR_CMD_REV "REV"
#define MOTOR_CMD_STOP "STOP"
#define MOTOR_DIR_PREFIX "DIR"
#define MOTOR_SPD_PREFIX "SPD"
#define MOTOR_STATE_PREFIX "STATE"

// ---------------------------------------------------------------------------
// Ultrasound (HC-SR04)
// ---------------------------------------------------------------------------
// Income:
//   US:US_<n>:PING
//
// Outcome:
//   US_<n>:DIST:<cm>
//   US_<n>:DIST:ERROR

#define ULTRASOUND_BASE_ID "US"
#define ULTRASOUND_ID(num) ULTRASOUND_BASE_ID "_" #num
#define ULTRASOUND_PING_COMMAND "PING"
#define ULTRASOUND_DISTANCE_MEASURED_PREFIX "DIST"

// ---------------------------------------------------------------------------
// Eyes (GC9A01 × 2)
// ---------------------------------------------------------------------------
// Income:
//   EYE:EYE_<n>:<gx>,<gy>,<r>,<g>,<b>
//       <gx/gy> : gaze offset, -100 to +100
//                 (mapped internally to ±MAX_GAZE pixels)
//       <r/g/b> : iris colour, 0-255 each
//
//   EYE:EYE_<n>:COLOR:<r>,<g>,<b>
//   EYE:EYE_<n>:SHAPE:<type>   (circle, star, smiley, x)
//
// Example:
//   EYE:EYE_1:30,-10,255,200,0
//   EYE:EYE_1:COLOR:255,0,0
//   EYE:EYE_1:SHAPE:star
//
// Outcome:
//   EYE_<n>:READY:ok
//   EYE_<n>:EYE:ok

#define EYE_BASE_ID "EYE"
#define EYE_ID(num) EYE_BASE_ID "_" #num
#define EYE_PREFIX "EYE"
#define EYE_READY_PREFIX "READY"
#define EYE_CMD_COLOR "COLOR"
#define EYE_CMD_SHAPE "SHAPE"

// ---------------------------------------------------------------------------

#endif // COMMUNICATION_PORTOCOL_DECLARATION_H