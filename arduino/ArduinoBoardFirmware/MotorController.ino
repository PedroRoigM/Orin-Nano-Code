#include "MotorController.h"

MotorController::MotorController(const String &id, int pinIn1, int pinIn2, int pinEn)
    : GeneralController(id, MOTOR_BASE_ID), _pinIn1(pinIn1), _pinIn2(pinIn2), _pinEn(pinEn)
{
    pinMode(_pinIn1, OUTPUT);
    pinMode(_pinIn2, OUTPUT);
    pinMode(_pinEn, OUTPUT);
    stop();
}

void MotorController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    // Exercise the message pipeline with protocol-style motor commands.
    Update(observerId + ":" + String(MOTOR_CMD_FWD) + ",80");
    delay(500);
    Update(observerId + ":" + String(MOTOR_CMD_STOP));

    Serial.println(F("PASS"));
}

void MotorController::Update(const String &message)
{
    parseMessage(message);
}

void MotorController::parseMessage(const String &message)
{
    int colonIndex = message.indexOf(':');
    if (colonIndex <= 0)
        return;

    String targetId = message.substring(0, colonIndex);
    String command  = message.substring(colonIndex + 1);

    if (targetId != observerId)
        return;

    // Command format (see CommunicationPortocolDeclaration.h):
    //   FWD,<speed> | REV,<speed> | STOP or STOP,<ignored>
    int commaIndex = command.indexOf(',');
    String direction = (commaIndex < 0) ? command : command.substring(0, commaIndex);
    int speed = 0;
    if (commaIndex >= 0)
    {
        speed = constrain(command.substring(commaIndex + 1).toInt(), 0, 255);
    }

    if (direction == MOTOR_CMD_STOP)
    {
        stop();
    }
    else
    {
        applyDirection(direction, speed);
    }
}

void MotorController::applyDirection(const String &direction, int speed)
{
    if (direction == "FWD")
    {
        digitalWrite(_pinIn1, HIGH);
        digitalWrite(_pinIn2, LOW);
        analogWrite(_pinEn, speed);
        sendToSerial("DIR:FWD,SPD:" + String(speed));
    }
    else if (direction == "REV")
    {
        digitalWrite(_pinIn1, LOW);
        digitalWrite(_pinIn2, HIGH);
        analogWrite(_pinEn, speed);
        sendToSerial("DIR:REV,SPD:" + String(speed));
    }
    else
    {
        stop();
    }
}

void MotorController::stop()
{
    digitalWrite(_pinIn1, LOW);
    digitalWrite(_pinIn2, LOW);
    analogWrite(_pinEn, 0);
    sendToSerial(F("STATE:STOP"));
}
