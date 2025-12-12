#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include "config.h"
#include "sensor_reader.h"
#include "servo_control.h"

// Протокол обміну JSON командами
class JsonParser {
 public:
  JsonParser(ServoControl &servoRef, SensorReader &sensorRef)
      : servo(servoRef), sensors(sensorRef) {}

  void handleInput(const String &payload) {
    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, payload);
    if (err) {
      if (Config::DEBUG_LOG) Serial.println(F("[JSON] Помилка парсингу"));
      return;
    }

    const char *cmd = doc["cmd"];
    if (!cmd) return;

    if (strcmp(cmd, "move_servo") == 0) {
      uint8_t servoIndex = doc["servo"] | 0;
      uint8_t angle = doc["angle"] | 0;
      servo.moveServo(servoIndex, angle);
      lastCommandAt = millis();
    } else if (strcmp(cmd, "read_sensors") == 0) {
      SensorData data = sensors.readAll();
      sendSensorReport(data);
      lastCommandAt = millis();
    } else if (strcmp(cmd, "emergency_stop") == 0) {
      emergencyStop();
    }
  }

  void emergencyStop() {
    servo.emergencyStop();
    sendSimpleAck(F("emergency_stop"));
    lastCommandAt = millis();
  }

  void sendSensorReport(const SensorData &data) {
    StaticJsonDocument<256> doc;
    doc["event"] = "sensors";
    JsonArray moisture = doc.createNestedArray("moisture");
    for (uint8_t i = 0; i < Config::MOISTURE_SENSOR_COUNT; ++i) {
      moisture.add(data.moisture[i]);
    }
    doc["light"] = data.light;

    serializeJson(doc, Serial);
    Serial.println();
  }

  void sendSimpleAck(const __FlashStringHelper *event) {
    StaticJsonDocument<128> doc;
    doc["event"] = event;
    serializeJson(doc, Serial);
    Serial.println();
  }

  unsigned long lastCommandTimestamp() const { return lastCommandAt; }

 private:
  ServoControl &servo;
  SensorReader &sensors;
  unsigned long lastCommandAt = 0;
};

