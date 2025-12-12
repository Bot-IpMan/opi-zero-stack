#pragma once

#include <Arduino.h>
#include "config.h"

struct SensorData {
  uint16_t moisture[Config::MOISTURE_SENSOR_COUNT];
  uint16_t light;
};

// Зчитування аналогових датчиків (вологість та освітленість)
class SensorReader {
 public:
  void begin() {
    for (uint8_t i = 0; i < Config::MOISTURE_SENSOR_COUNT; ++i) {
      pinMode(Config::MOISTURE_PINS[i], INPUT);
    }
    pinMode(Config::PHOTO_PIN, INPUT);
  }

  SensorData readAll() {
    SensorData data{};
    for (uint8_t i = 0; i < Config::MOISTURE_SENSOR_COUNT; ++i) {
      data.moisture[i] = analogRead(Config::MOISTURE_PINS[i]);
    }
    data.light = analogRead(Config::PHOTO_PIN);
    return data;
  }
};

