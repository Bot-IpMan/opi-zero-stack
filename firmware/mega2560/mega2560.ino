#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>

Adafruit_PWMServoDriver pwm(0x40);

static const uint8_t N = 6;   // кількість серв

// --- ДІАПАЗОН ПІД 90°-серво (можеш підкрутити на кожен канал) ---
int MIN_US[N] = {1250,1250,1250,1250,1250,1250};   // ≈ -45°
int MAX_US[N] = {1750,1750,1750,1750,1750,1750};   // ≈ +45°
// Для дуже малих тестових рухів зроби наприклад 1450..1550

const float CMD_GAIN = 0.10f; // було 0.20f
// або навіть 0.05f для ультраповільної калібровки

// --- ЛІМІТИ ШВИДКОСТІ (було: MAX_STEP_US=4, STEP_DELAY_MS=10) ---
const int MAX_STEP_US = 1;    // крок 1 мкс
const int STEP_DELAY_MS = 25; // пауза 25 мс
const int DEADBAND_US = 1;    // щоб повзти навіть на дрібних різницях

int last_us[N]; // остання позиція

inline int clampUs(int ch, int us){
  if (us < MIN_US[ch]) us = MIN_US[ch];
  if (us > MAX_US[ch]) us = MAX_US[ch];
  return us;
}

// Нормалізований 0..1 → у мкс з урахуванням CMD_GAIN навколо центру
int normToUsWithGain(int ch, float v){
  if (v < 0) v = 0; if (v > 1) v = 1;
  const int minv = MIN_US[ch];
  const int maxv = MAX_US[ch];
  const int mid  = (minv + maxv)/2;
  const int half = (maxv - minv)/2;
  // mapping: 0..1 → -1..+1 → стискаємо CMD_GAIN → додаємо до середини
  float x = (v - 0.5f) * 2.0f * CMD_GAIN;
  int us = (int)(mid + x * half + 0.5f);
  return clampUs(ch, us);
}

inline void writeUs(int ch, int us){
  us = clampUs(ch, us);
  pwm.writeMicroseconds(ch, us);
  last_us[ch] = us;
}

// Плавний рух з обмеженням швидкості (у мкс/крок)
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
        int step = (abs(d) > MAX_STEP_US) ? ( (d>0)? MAX_STEP_US : -MAX_STEP_US ) : d;
        writeUs(i, cur + step);
      }
    }
    delay(STEP_DELAY_MS);
  }
}

// Послідовне м’яке центрування (щоб не було піку струму)
void softCenter(){
  for (uint8_t i=0;i<N;i++){
    int mid = (MIN_US[i]+MAX_US[i])/2;
    last_us[i] = mid;
    writeUs(i, mid);
    delay(150); // по одному
  }
}

void setup(){
  Serial.begin(115200);
  while(!Serial){ delay(10); }

  Wire.begin();
  pwm.begin();
  pwm.setOscillatorFrequency(27000000); // опціонально, як стабілізатор
  pwm.setOutputMode(true);              // totem-pole
  pwm.setPWMFreq(50);
  delay(100);

  softCenter();
  Serial.println(F("READY"));
}

void loop(){
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length()==0) return;

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err){ Serial.print(F("ERR json_parse ")); Serial.println(err.c_str()); return; }

  if (!doc.containsKey("cmd")){ Serial.println(F("ERR missing_cmd")); return; }
  JsonArray cmd = doc["cmd"];
  if (cmd.size()!=N){ Serial.println(F("ERR cmd_size")); return; }

  int target_us[N];
  for (uint8_t i=0;i<N;i++){
    float v = cmd[i].as<float>();   // очікуємо 0.0..1.0
    target_us[i] = normToUsWithGain(i, v);
  }

  moveWithRateLimit(target_us);

  Serial.print(F("OK"));
  if (doc.containsKey("seq")){ Serial.print(F(" seq=")); Serial.print(doc["seq"].as<String>()); }
  Serial.println();
}
