// додай на початок
#define OE_PIN 7
bool ARMED = false;

void setup() {
  // ...
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);   // Вимкнути виходи PCA9685
  pwm.begin();
  pwm.setOutputMode(true);
  pwm.setPWMFreq(50);
  for (uint8_t i=0;i<N;i++) pwm.setPWM(i, 0, 0); // усе OFF
  Serial.println(F("READY DISARMED"));
}

// м'який центр тільки коли ARM
void armAndCenter() {
  digitalWrite(OE_PIN, LOW);    // дозволити виходи
  softCenter();
  ARMED = true;
  Serial.println(F("ARMED"));
}

void disarmAll() {
  for (uint8_t i=0;i<N;i++) pwm.setPWM(i, 0, 0); // усе OFF
  digitalWrite(OE_PIN, HIGH);   // вимкнути виходи
  ARMED = false;
  Serial.println(F("DISARMED"));
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n'); line.trim();
  if (!line.length()) return;

  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, line)) { Serial.println(F("ERR json_parse")); return; }

  if (doc.containsKey("arm") && doc["arm"]==true) { armAndCenter(); return; }
  if (doc.containsKey("arm") && doc["arm"]==false){ disarmAll();    return; }

  if (!ARMED) { Serial.println(F("ERR not_armed")); return; }

  // далі твоя обробка {"cmd":[...]} і moveWithRateLimit(...)
}
