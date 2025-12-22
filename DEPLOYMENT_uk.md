# 🚀 Розгортання Smart Greenhouse Stack

Покрокові інструкції для ПК (LLM координатор), Orange Pi Zero та прошивки Arduino Mega + PCA9685.

## 1) Попередні вимоги
- Docker 24+ та Docker Compose plugin.
- Python 3.10+ (для локальних запусків без контейнерів).
- `arduino-cli` для прошивки контролера.
- Доступ до брокера MQTT (локально або на ПК) та стабільна мережа між вузлами.

### Приклад середовищ
- `.env.example` — базові змінні для LLM-сервісу та Orange Pi.
- `pc-llm-service/config.yaml` — налаштування моделі, шляхів даних і MQTT.
- `app/gpio_config.yaml` — конфігурація пінів реле/датчиків для Orange Pi.

## 2) Розгортання на ПК (LLM + RAG)
```bash
# 1. Імпортуйте змінні або створіть .env
cp .env.example pc-llm-service/.env

# 2. Запустіть LLM сервіс (з опційним локальним MQTT профілем)
docker compose -f docker-compose.pc.yml up -d pc-llm-service
# Якщо потрібен локальний брокер на ПК:
docker compose -f docker-compose.pc.yml --profile with-mqtt up -d

# 3. Перевірте здоров'я API
curl http://localhost:8080/system_status
```
- Сервіс монтує `pc-llm-service/config.yaml`, `knowledge/` і `data/` у контейнер.
- Камера проброшується автоматично через `CAMERA_DEVICE` (за замовчуванням `/dev/video0`), але `make pc-up` автоматично запускає сервіс без пробросу, якщо пристрій відсутній.
- Для стабільної роботи на CPU без AVX задайте легкий ембединг через `EMBEDDING_MODEL` (за замовчуванням `BAAI/bge-small-en-v1.5`, FastEmbed) — це усуває падіння `pc-llm-service` з кодом 136.

## 3) Розгортання на Orange Pi Zero
```bash
# 1. Підготуйте змінні середовища
cp .env.example app/.env
sed -i 's/MQTT_HOST=.*/MQTT_HOST=192.168.1.220/' app/.env  # IP брокера/ПК

# 2. Запустіть застосунок і MQTT клієнт (host network для мінімальної затримки)
docker compose -f docker-compose.orangepi.yml up -d app mqttc

# 3. Перевірте здоров'я API Orange Pi
curl http://localhost:8000/healthz
```
- Контейнер отримує доступ до серійного порту через `SERIAL_DEV` та монтує `app/model.tflite`.
- Для швидкого доступу до MQTT використовується `network_mode: host`.

## 4) Скопіювати TFLite wheel з ПК (обхід компіляції)
**На ПК (або скачати):**
```bash
# 1. Запустіть скрипт, який скачає wheel та скопіює на Orange Pi
./app/scripts/copy_tflite_wheel.sh --host orangepi@192.168.1.101

# 2. Якщо потрібно лише скачати wheel локально:
./app/scripts/copy_tflite_wheel.sh --download-only
```
- Скрипт створює папку `app/wheels/` локально та копіює wheel у `~/opi-zero-stack/app/wheels/` на Orange Pi.
- Далі використовуйте wheel під час інсталяції залежностей (див. інструкції у `app/requirements-orangepi-zero.txt`).

## 5) Прошивка Arduino Mega + PCA9685
```bash
cd firmware/robotarm
arduino-cli core install arduino:avr
arduino-cli lib install "Adafruit PWM Servo Driver Library" "ArduinoJson"
arduino-cli compile --fqbn arduino:avr:mega robotarm.ino
arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:mega robotarm.ino
```
- Файл `config.h` містить пінмап та параметри сервоприводів.
- JSON протокол для команд/телеметрії описаний у `ARCHITECTURE_uk.md`.

## 6) Моніторинг та логування
- Папка `monitoring/` зарезервована під конфігурацію Prometheus/Grafana та експортери.
- Для перегляду логів контейнерів використовуйте:
```bash
docker compose -f docker-compose.pc.yml logs -f pc-llm-service
# або
sudo docker compose -f docker-compose.orangepi.yml logs -f app mqttc
```

## 7) Тести
```bash
# Локальні unit/integration тести
pytest -q

# Інтеграційний профіль через Docker
docker compose -f tests/docker-compose.test.yml up --build --abort-on-container-exit
```

## 8) Типові топіки MQTT
- `greenhouse/sensors/#` — телеметрія з Arduino/OPI.
- `greenhouse/cmd/actuators` — команди на актуатори (JSON payload).
- `greenhouse/llm/goals` — цілі від LLM/користувача.
- `greenhouse/events` — події/алерти.

> Порада: зберігайте `.env` для ПК та Orange Pi окремо; перед деплоєм оновлюйте IP брокера, порт та серійний інтерфейс.
