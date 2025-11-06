#define ARDUINOJSON_USE_LONG_LONG 1
#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>

constexpr uint8_t PCA9685_I2C_ADDR = 0x40;
constexpr uint16_t SERVO_MIN_US = 500;   // microseconds for fully retracted position
constexpr uint16_t SERVO_MAX_US = 2500;  // microseconds for fully extended position
constexpr uint16_t SERVO_NEUTRAL_US = (SERVO_MIN_US + SERVO_MAX_US) / 2;
constexpr uint16_t SERVO_WIGGLE_US = 150;  // +/- range for startup wiggle
constexpr float COMMAND_MIN = 0.0f;
constexpr float COMMAND_MAX = 1.0f;
constexpr uint8_t SERVO_CHANNELS[] = {0, 1, 2, 3, 4, 5};
constexpr size_t SERVO_COUNT = sizeof(SERVO_CHANNELS) / sizeof(SERVO_CHANNELS[0]);
constexpr uint8_t SERVO_PWM_FREQ = 50;  // Hz
constexpr size_t SERIAL_BUFFER_SIZE = 256;
constexpr uint32_t SERIAL_BAUD = 115200;

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(PCA9685_I2C_ADDR);

uint16_t currentServoPulse[SERVO_COUNT];
char serialBuffer[SERIAL_BUFFER_SIZE];
size_t serialBufferLen = 0;

void applyServoPulse(size_t index, uint16_t pulseUs) {
  if (index >= SERVO_COUNT) {
    return;
  }
  pwm.writeMicroseconds(SERVO_CHANNELS[index], pulseUs);
  currentServoPulse[index] = pulseUs;
}

uint16_t commandToPulse(float value) {
  if (value < COMMAND_MIN) {
    value = COMMAND_MIN;
  } else if (value > COMMAND_MAX) {
    value = COMMAND_MAX;
  }
  const float span = static_cast<float>(SERVO_MAX_US - SERVO_MIN_US);
  const float commandSpan = COMMAND_MAX - COMMAND_MIN;
  float normalized = 0.0f;
  if (commandSpan > 0.0001f) {
    normalized = (value - COMMAND_MIN) / commandSpan;
  }
  const float pulse = static_cast<float>(SERVO_MIN_US) + normalized * span;
  return static_cast<uint16_t>(pulse + 0.5f);
}

void wiggleServos() {
  for (size_t i = 0; i < SERVO_COUNT; ++i) {
    applyServoPulse(i, SERVO_NEUTRAL_US);
  }
  delay(400);

  for (size_t i = 0; i < SERVO_COUNT; ++i) {
    uint16_t low = SERVO_NEUTRAL_US > SERVO_WIGGLE_US ? SERVO_NEUTRAL_US - SERVO_WIGGLE_US : SERVO_MIN_US;
    uint16_t high = SERVO_NEUTRAL_US + SERVO_WIGGLE_US;
    if (high > SERVO_MAX_US) {
      high = SERVO_MAX_US;
    }
    applyServoPulse(i, low);
  }
  delay(250);
  for (size_t i = 0; i < SERVO_COUNT; ++i) {
    uint16_t high = SERVO_NEUTRAL_US + SERVO_WIGGLE_US;
    if (high > SERVO_MAX_US) {
      high = SERVO_MAX_US;
    }
    applyServoPulse(i, high);
  }
  delay(250);
  for (size_t i = 0; i < SERVO_COUNT; ++i) {
    applyServoPulse(i, SERVO_NEUTRAL_US);
  }
}

void sendError(const __FlashStringHelper *msg) {
  Serial.print(F("ERR "));
  Serial.println(msg);
}

void sendOk(const String &seqStr) {
  Serial.print(F("OK"));
  if (seqStr.length() > 0) {
    Serial.print(F(" seq="));
    Serial.print(seqStr);
  }
  Serial.println();
}

String unsignedLongLongToString(unsigned long long value) {
  char buffer[32];
  size_t index = 0;
  do {
    const unsigned long long digit = value % 10ULL;
    buffer[index++] = static_cast<char>('0' + digit);
    value /= 10ULL;
  } while (value > 0 && index < (sizeof(buffer) - 1));

  buffer[index] = '\0';

  for (size_t i = 0; i < index / 2; ++i) {
    char tmp = buffer[i];
    buffer[i] = buffer[index - 1 - i];
    buffer[index - 1 - i] = tmp;
  }

  return String(buffer);
}

String longLongToString(long long value) {
  if (value < 0) {
    const unsigned long long magnitude = static_cast<unsigned long long>(-(value + 1)) + 1ULL;
    String result = String('-');
    result += unsignedLongLongToString(magnitude);
    return result;
  }
  return unsignedLongLongToString(static_cast<unsigned long long>(value));
}

String extractSeqString(const JsonVariant &seqVariant) {
  if (seqVariant.isNull()) {
    return String();
  }
  if (seqVariant.is<const char *>()) {
    return String(seqVariant.as<const char *>());
  }
  if (seqVariant.is<long long>()) {
    return longLongToString(seqVariant.as<long long>());
  }
  if (seqVariant.is<unsigned long long>()) {
    return unsignedLongLongToString(seqVariant.as<unsigned long long>());
  }
  if (seqVariant.is<long>()) {
    return String(seqVariant.as<long>());
  }
  if (seqVariant.is<unsigned long>()) {
    return String(seqVariant.as<unsigned long>());
  }
  if (seqVariant.is<int>()) {
    return String(seqVariant.as<int>());
  }
  if (seqVariant.is<unsigned int>()) {
    return String(seqVariant.as<unsigned int>());
  }
  return String();
}

void processCommand(const char *payload) {
  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, payload);
  if (err != DeserializationError::Ok) {
    sendError(F("json_parse"));
    return;
  }

  JsonVariant seqVariant = doc["seq"];
  JsonArray cmd = doc["cmd"].as<JsonArray>();

  if (cmd.isNull()) {
    sendError(F("missing_cmd"));
    return;
  }
  if (cmd.size() != SERVO_COUNT) {
    sendError(F("cmd_size"));
    return;
  }

  float values[SERVO_COUNT];
  for (size_t i = 0; i < SERVO_COUNT; ++i) {
    if (!cmd[i].is<float>() && !cmd[i].is<double>()) {
      sendError(F("cmd_type"));
      return;
    }
    values[i] = cmd[i].as<float>();
    if (!isfinite(values[i])) {
      sendError(F("cmd_nan"));
      return;
    }
  }

  for (size_t i = 0; i < SERVO_COUNT; ++i) {
    const uint16_t pulse = commandToPulse(values[i]);
    applyServoPulse(i, pulse);
  }

  String seqStr = extractSeqString(seqVariant);
  sendOk(seqStr);
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  while (!Serial) {
    delay(10);
  }

  Wire.begin();
  Wire.setClock(400000);
  pwm.begin();
  pwm.setPWMFreq(SERVO_PWM_FREQ);
  delay(10);

  for (size_t i = 0; i < SERVO_COUNT; ++i) {
    currentServoPulse[i] = SERVO_NEUTRAL_US;
  }

  wiggleServos();
}

void loop() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      if (serialBufferLen > 0) {
        serialBuffer[serialBufferLen] = '\0';
        processCommand(serialBuffer);
        serialBufferLen = 0;
      }
      continue;
    }
    if (serialBufferLen + 1 >= SERIAL_BUFFER_SIZE) {
      serialBufferLen = 0;
      sendError(F("line_too_long"));
      // consume until newline
      while (Serial.available() > 0) {
        char discard = static_cast<char>(Serial.peek());
        if (discard == '\n') {
          Serial.read();
          break;
        }
        Serial.read();
      }
      continue;
    }
    serialBuffer[serialBufferLen++] = c;
  }
}
