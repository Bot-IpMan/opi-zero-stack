#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>

// ====== Налаштування безпеки ======
#define USE_OE 1          // 1 = керуємо OE апаратно (рекомендовано), 0 = без OE-піна
#define OE_PIN 7          // якщо USE_OE=1, під’єднай /OE плати PCA9685 до D7 МЕГА

// ====== Загальні параметри ======
Adafruit_PWMServoDriver pwm(0x40);

static const uint8_t N = 6;     // кількість серв на руці

// Діапазон для 90°-серво (стартово дуже вузький та безпечний)
// За потреби розширюй поступово — спершу відкалібруй кожен канал
int MIN_US[N] = {1450,1450,1450,1450,1450,1450};
int MAX_US[N] = {1550,1550,1550,1550,1550,1550};

// Акуратність команд 0..1: 0.10 = 10% від доступного ходу (дуже делікатно)
const float CMD_GAIN = 0.10f;

// Обмеження швидкості (10× повільніше)
const int   MAX_STEP_US   = 1;    // крок 1 мкс за ітерацію
const int   STEP_DELAY_MS = 25;   // пауза 25 мс між кроками
const int   DEADBAND_US   = 1;    // ігнорувати спроби руху <1 мкс

int  last_us[N];
bool ARMED = false;

// ====== Утиліти ======
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

// Послідовне м’яке центрування — без піків
void softCenter(){
  for (uint8_t i=0;i<N;i++){
    int mid = (MIN_US[i] + MAX_US[i]) / 2;
    last_us[i] = mid;
    writeUs(i, mid);
    delay(150); // по одному
  }
}

// ====== ARM / DISARM ======
void outputsOff(){
  for (uint8_t i=0;i<N;i++) pwm.setPWM(i, 0, 0); // повністю OFF
}

void armAndCenter(){
#if USE_OE
  digitalWrite(OE_PIN, LOW);  // дозволити виходи
#endif
  softCenter();
  ARMED = true;
  Serial.println(F("ARMED"));
}

void disarmAll(){
  outputsOff();
#if USE_OE
  digitalWrite(OE_PIN, HIGH); // вимкнути виходи драйвера
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
  pwm.setOscillatorFrequency(27000000); // опційно, стабілізує частоту
  pwm.setOutputMode(true);              // totem-pole
  pwm.setPWMFreq(50);
  delay(100);

#if USE_OE
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);  // по замовчуванню виходи вимкнені
#endif
  outputsOff();

  // Безпечне повідомлення про стан
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

  // Керування ARM
  if (doc.containsKey("arm")){
    bool v = doc["arm"];
    if (v) armAndCenter();
    else   disarmAll();
    return;
  }

  // Команди на рух
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
    float v = cmd[i].as<float>();    // 0.0..1.0
    target_us[i] = normToUsWithGain(i, v);
  }

  moveWithRateLimit(target_us);

  Serial.print(F("OK"));
  if (doc.containsKey("seq")){
    Serial.print(F(" seq=")); Serial.print(doc["seq"].as<String>());
  }
  Serial.println();
}
