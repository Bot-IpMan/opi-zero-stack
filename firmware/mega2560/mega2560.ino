#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>

// ====== MG90S-профіль + ультраповільний рух ======
// Під MG90S (центр ~1500 мкс; робочий діапазон 500–2500 мкс).
// Виходи вимкнені до ARM. Є prime/init, step-кроки, м’який rate-limit.

// ---- Безпечне керування OE (рекомендовано) ----
#define USE_OE 1           // 1 = керуємо OE апаратно, 0 = не використовуємо OE-пін
#define OE_PIN 7           // /OE на PCA9685 → D7 Arduino MEGA

Adafruit_PWMServoDriver pwm(0x40);
static const uint8_t N = 6; // кількість сервоканалів

// Стартовий безпечний хід (звужений). Потім розшириш по каналах.
int MIN_US[N] = {1200,1200,1200,1200,1200,1200};
int MAX_US[N] = {1800,1800,1800,1800,1800,1800};

// Наскільки команда 0..1 впливає на хід (0.5 = 50% від поточного діапазону)
const float CMD_GAIN = 0.50f;

// Повільність руху (≈10× повільніше за типове)
const int   MAX_STEP_US   = 1;    // мкс за ітерацію
const int   STEP_DELAY_MS = 25;   // мс між ітераціями
const int   DEADBAND_US   = 0;    // не «гасимо» дрібні кроки

int  last_us[N];
bool ARMED = false;

inline int clampUs(int ch, int us){
  if (us < MIN_US[ch]) us = MIN_US[ch];
  if (us > MAX_US[ch]) us = MAX_US[ch];
  return us;
}

int normToUsWithGain(int ch, float v){
  if (v < 0) v = 0; if (v > 1) v = 1;
  const int minv = MIN_US[ch], maxv = MAX_US[ch];
  const int mid  = (minv + maxv)/2;
  const int half = (maxv - minv)/2;
  float x = (v - 0.5f) * 2.0f * CMD_GAIN;  // -1..+1, стиснуто gain
  int us = (int)(mid + x * half + 0.5f);
  return clampUs(ch, us);
}

inline void writeUs(int ch, int us){
  us = clampUs(ch, us);
  pwm.writeMicroseconds(ch, us);
  last_us[ch] = us;
}

void outputsOff(){
  for (uint8_t i=0;i<N;i++) pwm.setPWM(i, 0, 0);
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

// Мікрокроки для одного каналу: du (мкс за крок), n (кількість), dly (мс)
void stepChannel(uint8_t ch, int du, int n, int dly){
  if (ch >= N) return;
  for (int k=0; k<n; k++){
    writeUs(ch, last_us[ch] + du);
    delay(dly);
  }
}

// ARM з опційною ініціалізацією (записуємо імпульси заздалегідь, поки OE=HIGH)
void armAndMaybeInit(const int *init_us){
  if (init_us){
    for (uint8_t i=0;i<N;i++){
      last_us[i] = clampUs(i, init_us[i]);
      pwm.writeMicroseconds(i, last_us[i]);
    }
  }
#if USE_OE
  digitalWrite(OE_PIN, LOW);   // увімкнути виходи
#endif
  ARMED = true;
  Serial.println(F("ARMED"));
}

void disarmAll(){
  outputsOff();
#if USE_OE
  digitalWrite(OE_PIN, HIGH);  // вимкнути виходи
#endif
  ARMED = false;
  Serial.println(F("DISARMED"));
}

void setup(){
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  Wire.begin();
  pwm.begin();
  pwm.setOscillatorFrequency(27000000);
  pwm.setOutputMode(true);
  pwm.setPWMFreq(50);
  delay(100);

#if USE_OE
  pinMode(OE_PIN, OUTPUT);
  digitalWrite(OE_PIN, HIGH);     // за замовчуванням виходи вимкнені
#endif
  outputsOff();

  for (uint8_t i=0;i<N;i++) last_us[i] = (MIN_US[i] + MAX_US[i]) / 2;

#if USE_OE
  Serial.println(F("READY DISARMED (OE) MG90S"));
#else
  Serial.println(F("READY DISARMED MG90S"));
#endif
}

void loop(){
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length()==0) return;

  StaticJsonDocument<384> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err){ Serial.print(F("ERR json_parse ")); Serial.println(err.c_str()); return; }

  // ---- ARM / DISARM ----
  if (doc.containsKey("arm")){
    bool v = doc["arm"];
    if (v){
      const int *init_ptr=nullptr; int init_buf[N];
      if (doc.containsKey("init")){
        JsonArray init = doc["init"];
        if (init.size()==N){
          for (uint8_t i=0;i<N;i++) init_buf[i] = init[i].as<int>();
          init_ptr = init_buf;
        }
      }
      armAndMaybeInit(init_ptr);
    } else {
      disarmAll();
    }
    return;
  }

  // ---- PRIME: попередньо записати мікросекунди (поки виходи вимкнені) ----
  if (doc.containsKey("prime")){
    JsonArray a = doc["prime"];
    if (a.size()!=N){ Serial.println(F("ERR prime_size")); return; }
    for (uint8_t i=0;i<N;i++){
      int us = a[i].as<int>();
      last_us[i] = clampUs(i, us);
      pwm.writeMicroseconds(i, last_us[i]);
    }
    Serial.println(F("OK prime"));
    return;
  }

  // ---- STEP для одного каналу ----
  if (doc.containsKey("step")){
    if (!ARMED){ Serial.println(F("ERR not_armed")); return; }
    JsonObject st = doc["step"];
    uint8_t ch = st["ch"] | 0;
    int du     = st["du"] | 10;
    int n      = st["n"]  | 10;
    int dly    = st["dly"]| 40;
    stepChannel(ch, du, n, dly);
    Serial.println(F("OK step"));
    return;
  }

  // ---- Зміна меж діапазону під канал під час роботи ----
  if (doc.containsKey("setRange")){
    JsonObject sr = doc["setRange"];
    uint8_t ch = sr["ch"] | 255;
    if (ch < N){
      MIN_US[ch] = sr["min"] | MIN_US[ch];
      MAX_US[ch] = sr["max"] | MAX_US[ch];
      if (MIN_US[ch] > MAX_US[ch]) { int t=MIN_US[ch]; MIN_US[ch]=MAX_US[ch]; MAX_US[ch]=t; }
      last_us[ch] = constrain(last_us[ch], MIN_US[ch], MAX_US[ch]);
      Serial.println(F("OK setRange"));
    } else {
      Serial.println(F("ERR ch_range"));
    }
    return;
  }

  // ---- Команда позицій для всіх каналів ----
  if (!doc.containsKey("cmd")){ Serial.println(F("ERR missing_cmd")); return; }
  if (!ARMED){ Serial.println(F("ERR not_armed")); return; }

  JsonArray cmd = doc["cmd"];
  if (cmd.size()!=N){ Serial.println(F("ERR cmd_size")); return; }

  int target_us[N];
  for (uint8_t i=0;i<N;i++){
    float v = cmd[i].as<float>();      // 0.0..1.0
    target_us[i] = normToUsWithGain(i, v);
  }
  moveWithRateLimit(target_us);

  Serial.print(F("OK"));
  if (doc.containsKey("seq")){ Serial.print(F(" seq=")); Serial.print(doc["seq"].as<String>()); }
  Serial.println();
}
