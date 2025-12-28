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

## 🧰 Makefile-команди для ПК та Orange Pi
Для зручності є окремі команди для кожної платформи. Логіка проста: префікс `pc-` для ПК і `opi-` для Orange Pi.

**ПК:**
- Збірка: `make pc-build`
- Запуск: `make pc-up`
- Логи: `make pc-logs`
- Shell: `make pc-shell`
- Зупинка: `make pc-down`

**Orange Pi Zero:**
- Збірка: `make opi-build`
- Запуск: `make opi-up`
- Логи: `make opi-logs`
- Shell: `make opi-shell`
- Зупинка: `make opi-down`
- Якщо Arduino з'являється як інший порт (наприклад, `/dev/ttyUSB0`), задайте `SERIAL_DEV=/dev/ttyUSB0 make opi-up`.

> Підказка: `make help` покаже повний список команд, включно з діагностикою та моніторингом.

## 🛠️ Усунення помилки `ModuleNotFoundError: No module named 'cv2'`
Якщо контейнер `robot-app` постійно перезапускається і в логах з'являється помилка про відсутність `cv2`, виконайте:

1. **Подивіться логи сервісу.**
   ```bash
docker compose logs -f robot-app
```
   Якщо бачите `ModuleNotFoundError: No module named 'cv2'`, образ зібрано без OpenCV.

2. **Перезберіть образ з OpenCV.**
   У `app/Dockerfile` вже є установка `python3-opencv` та `libopencv-dev`. Переконайтеся, що збираєте саме його:
   ```bash
docker compose build --no-cache robot-app
docker compose up -d robot-app
```

3. **Швидка перевірка всередині свіжого контейнера.**
   Запустіть окремий одноразовий контейнер і провалідуйте наявність модуля:
   ```bash
docker compose run --rm robot-app python - <<'PY'
import cv2
print(cv2.__version__)
PY
```
   Якщо команда проходить, сервіс стартує без помилки; якщо ні — перевірте, що build не пропускає кроки з apt/pip.
