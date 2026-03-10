#include "NeckController.h"

NeckController::NeckController(const String &id, int pinPan, int pinTilt)
    : GeneralController(id, NECK_BASE_ID),
      _pinPan(pinPan), _pinTilt(pinTilt),
      _currentPan(PAN_CENTER), _currentTilt(TILT_CENTER),
      _targetPan(PAN_CENTER), _targetTilt(TILT_CENTER),
      _isMoving(false)
{
    _servoPan.attach(_pinPan);
    _servoTilt.attach(_pinTilt);

    _servoPan.write(_currentPan);
    _servoTilt.write(_currentTilt);
}

void NeckController::sanityTest()
{
    Serial.print(F("[SanityTest] "));
    Serial.print(observerId);
    Serial.print(F(" ... "));

    // Move to center
    setTarget(PAN_CENTER, TILT_CENTER);
    while (_isMoving) loop();

    delay(100);

    // Test a slight movement
    setTarget(85, 95);
    while (_isMoving) loop();

    delay(100);

    // Center again
    setTarget(PAN_CENTER, TILT_CENTER);
    while (_isMoving) loop();

    Serial.println(F("PASS"));
}

void NeckController::Update(const String &message)
{
    parseMessage(message);
}

void NeckController::parseMessage(const String &message)
{
    int colonIndex = message.indexOf(':');
    if (colonIndex <= 0)
        return;

    String targetId = message.substring(0, colonIndex);
    String payload  = message.substring(colonIndex + 1);

    // Python test sends: NECK:SRV_1:<pan>,<tilt>
    // New standard could be: NECK:NECK_1:MOVE:<pan>,<tilt>
    if (targetId != observerId && targetId != "SRV_1")
        return;

    if (payload.startsWith(NECK_CMD_MOVE ":")) {
        payload = payload.substring(String(NECK_CMD_MOVE ":").length());
    }

    int commaIndex = payload.indexOf(',');
    if (commaIndex < 0)
        return;

    int pan = payload.substring(0, commaIndex).toInt();
    int tilt = payload.substring(commaIndex + 1).toInt();

    setTarget(pan, tilt);
}

void NeckController::setTarget(int pan, int tilt)
{
    pan = constrain(pan, PAN_MIN, PAN_MAX);
    tilt = constrain(tilt, TILT_MIN, TILT_MAX);

    _startPan = _currentPan;
    _startTilt = _currentTilt;
    _targetPan = pan;
    _targetTilt = tilt;

    _moveStartTime = millis();
    _isMoving = true;

    // Send the ACK equivalent
    sendToSerial(String(NECK_POS_PREFIX) + ":" + String(_targetPan) + "," + String(_targetTilt));
}

void NeckController::loop()
{
    if (!_isMoving)
        return;

    unsigned long elapsed = millis() - _moveStartTime;
    if (elapsed >= MOVE_DURATION_MS)
    {
        _currentPan = _targetPan;
        _currentTilt = _targetTilt;
        _isMoving = false;
    }
    else
    {
        float progress = (float)elapsed / MOVE_DURATION_MS;
        _currentPan = _startPan + progress * (_targetPan - _startPan);
        _currentTilt = _startTilt + progress * (_targetTilt - _startTilt);
    }

    _servoPan.write(_currentPan);
    _servoTilt.write(_currentTilt);
}
