#include <avr/wdt.h>
#include <Wire.h>
#include "config.h"
#include "json_parser.h"
#include "sensor_reader.h"
#include "servo_control.h"

ServoControl servoControl;
SensorReader sensorReader;
JsonParser parser(servoControl, sensorReader);

String inputBuffer;
unsigned long lastSensorReport = 0;
bool isEmergency = false;

void setup() {
  Serial.begin(Config::SERIAL_BAUD);
  Wire.begin();

  if (Config::DEBUG_LOG) Serial.println(F("[Init] Старт прошивки роботизованої руки"));

  for (uint8_t i = 0; i < Config::RELAY_COUNT; ++i) {
    pinMode(Config::RELAY_PINS[i], OUTPUT);
    digitalWrite(Config::RELAY_PINS[i], LOW); // початково вимкнено
  }

  sensorReader.begin();
  servoControl.begin();

  // Увімкнути watchdog (2 секунди). Скидаємо у loop.
  wdt_enable(WDTO_2S);
}

void loop() {
  readSerialCommands();
  handleCommunicationTimeout();
  handlePeriodicSensorReport();

  // Подаємо "корм" watchdog'у після успішного проходження усіх задач
  wdt_reset();
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      parser.handleInput(inputBuffer);
      // Якщо зв'язок відновлено командою — знімаємо прапорець аварії
      isEmergency = false;
      inputBuffer = "";
    } else {
      inputBuffer += c;
    }
  }
}

void handleCommunicationTimeout() {
  unsigned long now = millis();
  if (parser.lastCommandTimestamp() == 0) {
    // ще не було команд
    return;
  }

  if (!isEmergency && now - parser.lastCommandTimestamp() > Config::COMMUNICATION_TIMEOUT_MS) {
    isEmergency = true;
    if (Config::DEBUG_LOG) Serial.println(F("[Safety] Втрачено зв'язок. Аварійна зупинка."));
    parser.emergencyStop();
  }
}

void handlePeriodicSensorReport() {
  unsigned long now = millis();
  if (now - lastSensorReport < Config::SENSOR_READ_INTERVAL_MS) return;

  SensorData data = sensorReader.readAll();
  parser.sendSensorReport(data);
  lastSensorReport = now;
}

// Додаткові утиліти керування реле
void setRelay(uint8_t relayIndex, bool enabled) {
  if (relayIndex >= Config::RELAY_COUNT) return;
  digitalWrite(Config::RELAY_PINS[relayIndex], enabled ? HIGH : LOW);
}

