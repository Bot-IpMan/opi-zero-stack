#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>

// ====== КОНФІГ БЕЗПЕКИ ======
#define USE_OE 1          // 1 = керуємо OE апаратно (рекомендовано), 0 = без OE-піна
#define OE_PIN 7          // якщо USE_OE=1, під’єднай /OE (Output Enable) плати PCA9685 до D7 MEGA

// ====== ЗАГАЛЬНІ ПАРАМЕТРИ ======
Adafruit_PWMServoDriver pwm(0x40);
static const uint8_t N = 6;     // кількість сервоканалів

// Стартово дуже вузький і безпечний діапазон (≈1500 ±50 мкс) — розширюй після калібрування
int MIN_US[N] = {1450,1450,1450,1450,1450,1450};
int MAX_US[N] = {1550,1550,1550,1550,1550,1550};

// Наскільки частка команди 0..1 впливає на хід (0.10 = 10% від доступного діапазону)
const float CMD_GAIN = 0.10f;

// Обмеження швидкості (дуже повільно)
const int   MAX_STEP_US   = 1;    // крок 1 мкс за ітерацію
const int   STEP_DELAY_MS = 25;   // пауза 25 мс між ітераціями
const int   DEADBAND_US   = 1;    // ігнорувати похибки <1 мкс

int  last_us[N];
bool ARMED = false;

// ====== УТИЛІТИ ======
inline int clampUs(int ch, int us){
  if (us < MIN_US[ch]) us = MIN_US[ch];
  if (us > MAX_US[ch]) us = MAX_US[ch];
  return us;
}

int normToUsWithGain(int ch, float v){
  if (v < 0) v = 0; if (v > 1) v = 1;
  const int minv = MIN_US[ch];
  const int maxv = MAX_US[ch];
  const int mid  = (minv + maxv)/2;
  const int half = (maxv - minv)/2;
  float x = (v - 0.5f) * 2.0f * CMD_GAIN;   // -1..+1, стиснуто CMD_GAIN
  int us = (int)(mid + x * half + 0.5f);
  return clampUs(ch, us);
}

inline void writeUs(int ch, int us){
  us = clampUs(ch, us);
  pwm.writeMicroseconds(ch, us);
  last_us[ch] = us;
}

// Плавний рух з обмеженням швидкості
void moveWithRateLimit(const int target_us[]){
  bool done = false;
  while (!done){
    done = true;
    for (uint8_t i=0;i<N;i++){
      int cur = last_us[i];
      int tgt = clampUs(i, target_us[i]);
      int d   = tgt - cur;
      if (abs(d) > DEADBAND_US){
        done = false;
        int step = (abs(d) > MAX_STEP_US) ? ((d>0)? +MAX_STEP_US : -MAX_STEP_US) : d;
        writeUs(i, cur + step);
      }
    }
    delay(STEP_DELAY_MS);
  }
}

// Повністю вимкнути всі канали (без утримання)
void outputsOff(){
  for (uint8_t i=0;i<N;i++) pwm.setPWM(i, 0, 0);
}

// Мікрокроки для одного каналу: ch — канал, du — крок у мкс (може бути від’ємний), n — к-сть кроків
void stepChannel(uint8_t ch, int du, int n, int dly=25){
  for (int k=0; k<n; k++){
    int next = last_us[ch] + du;
    writeUs(ch, next);
    delay(dly);
  }
}

// ====== ARM / DISARM ======
void armAndCenter(){
#if USE_OE
  digitalWrite(OE_PIN, LOW);     // дозволити виходи драйвера
#endif
  // Без автопозиціювання: серви не рухаються до першої команди
  ARMED = true;
  Serial.println(F("ARMED"));
}

void disarmAll(){
  outputsOff();
#if USE_OE
  digitalWrite(OE_PIN, HIGH);    // вимкнути виходи драйвера
#endif
  ARMED = false;
  Serial.println(F("DISARMED"));
}

// ====== SETUP / LOOP ======
void setup(){
  Serial.begin(115200);
  while(!Serial){ delay(10); }

  Wire.begin();
  pwm.begin();
  pwm.setOscillatorFrequency(27000000); // опціонально для стабільності
  pwm.setOutputMode(true);              // totem-pole
  pwm.setPWMFreq(50);
  delay(100);

#if USE_OE
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);           // за замовчуванням виходи ВИМКНЕНО
#endif
  outputsOff();

  // Ініціалізуємо внутрішній стан (без руху): ставимо "уявний" середній
  for (uint8_t i=0;i<N;i++){
    last_us[i] = (MIN_US[i] + MAX_US[i]) / 2;
  }

#if USE_OE
  Serial.println(F("READY DISARMED (OE)"));
#else
  Serial.println(F("READY DISARMED"));
#endif
}

void loop(){
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err){
    Serial.print(F("ERR json_parse ")); Serial.println(err.c_str());
    return;
  }

  // ---- ARM / DISARM ----
  if (doc.containsKey("arm")){
    bool v = doc["arm"];
    if (v) armAndCenter();
    else   disarmAll();
    return;
  }

  // ---- STEP-режим для одного каналу ----
  if (doc.containsKey("step")){
    if (!ARMED){ Serial.println(F("ERR not_armed")); return; }
    JsonObject st = doc["step"];
    uint8_t ch = st["ch"] | 0;
    int du     = st["du"] | 1;     // мкс за крок
    int n      = st["n"]  | 10;    // кількість кроків
    int dly    = st["dly"]| 25;    // мс між кроками
    if (ch >= N){ Serial.println(F("ERR ch_range")); return; }
    stepChannel(ch, du, n, dly);
    Serial.println(F("OK step"));
    return;
  }

  // ---- Команда позицій для всіх каналів ----
  if (!ARMED){
    Serial.println(F("ERR not_armed"));
    return;
  }
  if (!doc.containsKey("cmd")){
    Serial.println(F("ERR missing_cmd"));
    return;
  }
  JsonArray cmd = doc["cmd"];
  if (cmd.size() != N){
    Serial.println(F("ERR cmd_size"));
    return;
  }

  int target_us[N];
  for (uint8_t i=0;i<N;i++){
    float v = cmd[i].as<float>();      // очікуємо 0.0..1.0
    target_us[i] = normToUsWithGain(i, v);
  }

  moveWithRateLimit(target_us);

  Serial.print(F("OK"));
  if (doc.containsKey("seq")){
    Serial.print(F(" seq=")); Serial.print(doc["seq"].as<String>());
  }
  Serial.println();
}
