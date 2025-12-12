# 🌱 Smart Greenhouse Stack (Ukr)

Оновлена збірка для керування роборукою та міні-теплицею: ПК з LLM планує дії, Orange Pi Zero маршрутизує команди та телеметрію, Arduino Mega + PCA9685 виконує керування в реальному часі.

## 📦 Структура фінального проекту
```
opi-zero-stack/
│
├── 🖥️ pc-llm-service/              # ПК координатор
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── llm_service.py
│   ├── vision_processor.py
│   ├── mqtt_client.py
│   ├── config.yaml
│   ├── rag/
│   │   ├── vector_store.py
│   │   ├── embeddings.py
│   │   └── retriever.py
│   └── knowledge/
│       ├── plants_care.json
│       ├── watering_schedule.json
│       └── disease_detection.json
│
├── 🍊 app/                         # Orange Pi Zero
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── pc_client.py
│   ├── sensors/
│   │   ├── bme280.py
│   │   ├── vl53l0x.py
│   │   └── manager.py
│   ├── actuators/
│   │   ├── relay.py
│   │   └── manager.py
│   └── gpio_config.yaml
│
├── 📟 firmware/                    # Arduino
│   ├── robotarm/
│   │   ├── robotarm.ino
│   │   ├── servo_control.h
│   │   ├── sensor_reader.h
│   │   └── json_parser.h
│   └── README_uk.md
│
├── 🐳 Docker конфігурації
│   ├── docker-compose.pc.yml       # ПК
│   └── docker-compose.orangepi.yml # Orange Pi
│
├── 📊 monitoring/
│   ├── docker-compose.monitoring.yml
│   ├── prometheus/
│   ├── grafana/
│   └── exporters/
├── 🧪 tests/
├── 📁 mosquitto/
├── 🗂️ training/
├── Makefile
├── README_uk.md
├── ARCHITECTURE_uk.md
├── DEPLOYMENT_uk.md
└── .env.example
```

## 🔍 Що де лежить
- **pc-llm-service/** — FastAPI + Ollama/LLM координатор, RAG для знань, MQTT клієнт і обробка відео.
- **app/** — сервіс Orange Pi Zero з API, GPIO/Serial роботою, клієнтом до ПК та прикладним TFLite-моделем.
- **firmware/** — прошивка Arduino Mega для керування сервоприводами й реле з JSON протоколом.
- **docker-compose.*.yml** — окремі оркестрації для ПК та Orange Pi; тестовий профіль у `docker-compose.test.yml`.
- **monitoring/** — місце для Prometheus/Grafana та експортерів.
- **tests/** — pytest unit/integration сценарії, docker-compose для інтеграції.
- **ARCHITECTURE_uk.md** — деталізація нової архітектури.
- **DEPLOYMENT_uk.md** — покрокове розгортання для ПК, Orange Pi та Arduino.

## 🚀 Швидкий старт
- Запуск LLM-сервісу на ПК: `docker compose -f docker-compose.pc.yml up -d` (додайте профіль `with-mqtt`, якщо потрібен локальний брокер).
- Запуск шлюзу на Orange Pi: `docker compose -f docker-compose.orangepi.yml up -d app mqttc`.
- Прошивка Arduino: `arduino-cli compile --fqbn arduino:avr:mega robotarm/robotarm.ino && arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:mega robotarm/robotarm.ino`.
