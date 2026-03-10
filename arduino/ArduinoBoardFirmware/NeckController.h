#ifndef NECK_CONTROLLER_H
#define NECK_CONTROLLER_H

#include "GeneralController.h"
#include <Servo.h>

class NeckController : public GeneralController
{
public:
    NeckController(const String &id, int pinPan, int pinTilt);

    void sanityTest();
    void Update(const String &message) override;
    void loop();

protected:
    void parseMessage(const String &message) override;

private:
    int _pinPan;
    int _pinTilt;
    Servo _servoPan;
    Servo _servoTilt;

    // Movement state
    int _currentPan;
    int _currentTilt;
    int _targetPan;
    int _targetTilt;

    int _startPan;
    int _startTilt;
    unsigned long _moveStartTime;
    bool _isMoving;

    static const int PAN_MIN = 70;
    static const int PAN_MAX = 110;
    static const int TILT_MIN = 80;
    static const int TILT_MAX = 100;
    static const int PAN_CENTER = 90;
    static const int TILT_CENTER = 90;

    // Smoothing duration: ~24ms to match demo delay(8) * 3 steps
    static const unsigned long MOVE_DURATION_MS = 24; 

    void setTarget(int pan, int tilt);
};

#endif // NECK_CONTROLLER_H
