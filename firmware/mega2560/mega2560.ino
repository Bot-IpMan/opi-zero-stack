#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>

Adafruit_PWMServoDriver pwm(0x40);

static const uint8_t N = 6;         // кількість серв
// Калібруй під свою механіку (старт безпечно: 900..2100)
int MIN_US[N] = { 900, 900, 900, 900, 900, 900 };
int MAX_US[N] = {2100,2100,2100,2100,2100,2100 };

int last_us[N]; // остання позиція, щоб рухатись плавно

int clampUs(int ch, int us){
  if (us < MIN_US[ch]) us = MIN_US[ch];
  if (us > MAX_US[ch]) us = MAX_US[ch];
  return us;
}

int normToUs(int ch, float v){               // v ∈ [0.0..1.0]
  if (v < 0) v = 0; if (v > 1) v = 1;
  long span = (long)MAX_US[ch] - MIN_US[ch];
  return (int)(MIN_US[ch] + (span * v + 0.5));
}

void writeUs(int ch, int us){
  pwm.writeMicroseconds(ch, clampUs(ch, us));
  last_us[ch] = clampUs(ch, us);
}

// Плавний груповий рух без піків
void moveBatchSmooth(int target_us[], int steps=20, int stepDelay=10){
  int start[N];
  for (uint8_t i=0;i<N;i++) start[i] = last_us[i];
  for (int s=1; s<=steps; s++){
    for (uint8_t i=0;i<N;i++){
      long v = start[i] + (long)(target_us[i]-start[i]) * s / steps;
      writeUs(i, (int)v);
    }
    delay(stepDelay);
  }
}

// Послідовне «м’яке» центрування на старті
void softCenter(){
  for (uint8_t i=0;i<N;i++){
    int mid = (MIN_US[i]+MAX_US[i])/2;
    // стартуємо з поточного last_us (якщо живлення щойно подали — візьмемо середину)
    last_us[i] = mid;
    writeUs(i, mid);
    delay(120);                 // НЕ всі одразу
  }
}

void setup() {
  Serial.begin(115200);
  while(!Serial) { delay(10); }

  Wire.begin();
  // Wire.setClock(400000);     // можна швидший I2C, не обов'язково
  pwm.begin();
  pwm.setOscillatorFrequency(27000000); // калібрує частоту, не обов’язково, але корисно
  pwm.setOutputMode(true);              // totem-pole, не open-drain
  pwm.setPWMFreq(50);
  pwm.setPWMFreq(50);
  delay(100);

  softCenter();                 // без ривка
  Serial.println(F("READY"));
}

void loop() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length()==0) return;

  StaticJsonDocument<256> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err){ Serial.print(F("ERR json_parse ")); Serial.println(err.c_str()); return; }

  if (!doc.containsKey("cmd")) { Serial.println(F("ERR missing_cmd")); return; }
  JsonArray cmd = doc["cmd"];
  if (cmd.size()!=N) { Serial.println(F("ERR cmd_size")); return; }

  int target_us[N];
  for (uint8_t i=0;i<N;i++){
    float v = cmd[i].as<float>();          // очікуємо 0.0..1.0
    target_us[i] = clampUs(i, normToUs(i, v));
  }

  // Плавний рух, невеликими кроками (всі разом, але делікатно)
  moveBatchSmooth(target_us, /*steps=*/25, /*stepDelay=*/8);

  Serial.print(F("OK"));
  if (doc.containsKey("seq")){ Serial.print(F(" seq=")); Serial.print(doc["seq"].as<String>()); }
  Serial.println();
}
