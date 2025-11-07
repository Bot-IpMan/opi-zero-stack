// Мінімальний тестовий скетч для перевірки зв'язку
// Завантажте цей скетч, якщо основний не компілюється

#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>
#include <ArduinoJson.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

void setup() {
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  
  Wire.begin();
  pwm.begin();
  pwm.setPWMFreq(50);
  delay(100);
  
  // Центруємо всі сервоприводи
  for (int i = 0; i < 6; i++) {
    pwm.writeMicroseconds(i, 1500);  // Нейтральна позиція
  }
  
  Serial.println(F("READY"));
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    
    if (line.length() == 0) return;
    
    // Парсимо JSON
    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, line);
    
    if (err) {
      Serial.print(F("ERR json_parse: "));
      Serial.println(err.c_str());
      return;
    }
    
    // Перевіряємо наявність "cmd"
    if (!doc.containsKey("cmd")) {
      Serial.println(F("ERR missing_cmd"));
      return;
    }
    
    JsonArray cmd = doc["cmd"];
    if (cmd.size() != 6) {
      Serial.println(F("ERR cmd_size"));
      return;
    }
    
    // Застосовуємо команди до сервоприводів
    for (int i = 0; i < 6; i++) {
      float value = cmd[i];
      
      // Конвертуємо 0.0-1.0 в мікросекунди (500-2500)
      int pulse = 500 + (int)(value * 2000.0);
      
      // Обмежуємо діапазон
      if (pulse < 500) pulse = 500;
      if (pulse > 2500) pulse = 2500;
      
      pwm.writeMicroseconds(i, pulse);
    }
    
    // Відповідаємо OK з seq (якщо є)
    Serial.print(F("OK"));
    if (doc.containsKey("seq")) {
      Serial.print(F(" seq="));
      Serial.print(doc["seq"].as<String>());
    }
    Serial.println();
  }
}
