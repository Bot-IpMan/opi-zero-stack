#pragma once

#include <Arduino.h>

// Конфігураційні параметри для роботизованої руки
namespace Config {
// === Параметри серво ===
static const uint8_t SERVO_COUNT = 6;
static const uint16_t SERVO_MIN_US[SERVO_COUNT] = {500, 520, 510, 500, 520, 510};
static const uint16_t SERVO_MAX_US[SERVO_COUNT] = {2500, 2480, 2490, 2500, 2480, 2490};
static const uint16_t SERVO_NEUTRAL_US[SERVO_COUNT] = {1500, 1500, 1500, 1500, 1500, 1500};

// PWM драйвер PCA9685
static const uint8_t PCA9685_ADDR = 0x40;
static const uint16_t PWM_FREQUENCY = 50; // 50 Гц для серво

// === Аналогові датчики ===
static const uint8_t MOISTURE_PINS[] = {A0, A1, A2, A3};
static const uint8_t MOISTURE_SENSOR_COUNT = sizeof(MOISTURE_PINS) / sizeof(uint8_t);
static const uint8_t PHOTO_PIN = A4;

// === Реле ===
static const uint8_t RELAY_PINS[] = {7, 8};
static const uint8_t RELAY_COUNT = sizeof(RELAY_PINS) / sizeof(uint8_t);

// Безпека
static const unsigned long COMMUNICATION_TIMEOUT_MS = 5000; // 5 секунд без команд -> аварійна зупинка
static const unsigned long SENSOR_READ_INTERVAL_MS = 2000;  // Час між автоматичними опитуваннями

// Комунікація
static const uint32_t SERIAL_BAUD = 115200;

// Відлагодження
static const bool DEBUG_LOG = true;
} // namespace Config
