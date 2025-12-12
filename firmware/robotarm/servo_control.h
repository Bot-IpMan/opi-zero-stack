#pragma once

#include <Adafruit_PWMServoDriver.h>
#include <Arduino.h>
#include "config.h"

// Логіка керування сервоприводами з урахуванням калібрування
class ServoControl {
 public:
  void begin() {
    pwm = Adafruit_PWMServoDriver(Config::PCA9685_ADDR);
    pwm.begin();
    pwm.setPWMFreq(Config::PWM_FREQUENCY);
    delay(10);
    if (Config::DEBUG_LOG) {
      Serial.println(F("[Servo] PCA9685 ініціалізовано"));
    }
    moveAllToNeutral();
  }

  void moveServo(uint8_t servoIndex, uint8_t angleDeg) {
    if (servoIndex >= Config::SERVO_COUNT) return;
    angleDeg = constrain(angleDeg, 0, 180);
    uint16_t pulse = angleToPulse(servoIndex, angleDeg);
    pwm.setPWM(servoIndex, 0, pulse);
  }

  void moveAllToNeutral() {
    for (uint8_t i = 0; i < Config::SERVO_COUNT; ++i) {
      uint16_t neutralPulse = Config::SERVO_NEUTRAL_US[i];
      uint16_t off = usToPwm(neutralPulse);
      pwm.setPWM(i, 0, off);
    }
  }

  void emergencyStop() {
    // При аварії переводимо серво у безпечний нейтральний стан
    moveAllToNeutral();
  }

 private:
  Adafruit_PWMServoDriver pwm;

  uint16_t angleToPulse(uint8_t servoIndex, uint8_t angleDeg) {
    uint16_t minUs = Config::SERVO_MIN_US[servoIndex];
    uint16_t maxUs = Config::SERVO_MAX_US[servoIndex];
    uint16_t pulseUs = map(angleDeg, 0, 180, minUs, maxUs);
    return usToPwm(pulseUs);
  }

  uint16_t usToPwm(uint16_t microseconds) {
    // 12-бітний PWM (4096 кроків), період 20 мс для серво при 50 Гц
    float pulseLength = 1000000.0f;      // 1,000,000 мкс у секунді
    pulseLength /= Config::PWM_FREQUENCY; // мкс на один період
    pulseLength /= 4096.0f;              // мкс на один крок
    return static_cast<uint16_t>(microseconds / pulseLength);
  }
};

