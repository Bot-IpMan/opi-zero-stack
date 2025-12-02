# 🦾 Robot Arm: YOLO + RL Control System

Розподілена система керування 6-DOF роботизованою рукою з використанням компʼютерного зору та навчанням з підкріпленням.

**Архітектура**: ПК (навчання) → Orange Pi PC (YOLO детекція) → Orange Pi Zero (RL контроль) → Arduino Mega → Роборука

---

## 📋 Зміст

1. [Що це?](#що-це)
2. [Як воно працює?](#як-воно-працює)
3. [Вимоги](#вимоги)
4. [Встановлення](#встановлення)
5. [Навчання (ПК)](#навчання-пк)
6. [Розгортання (Orange Pi)](#розгортання-orange-pi)
7. [Запуск](#запуск)
8. [Діагностика](#діагностика)
9. [Структура проекту](#структура-проекту)

---

## 🤔 Що це?

Це **гібридна система** для автоматичного керування роботизованою рукою:

### Проблема, яку вирішує:

Традиційні робо-руки потребують:
- ❌ Ручного програмування кожної задачі
- ❌ Потужного комп'ютера на борту
- ❌ Дорогих сенсорів

### Наше рішення:

- ✅ **Система навчається** самостійно через Reinforcement Learning (RL)
- ✅ **Розпізнає об'єкти** з камери через YOLO (You Only Look Once)
- ✅ **Мінімальні ресурси**: Orange Pi Zero (512MB RAM!)
- ✅ **Швидкий контроль**: 20 Hz на Orange Pi Zero, 30 FPS на Orange Pi PC

### Практичні приклади використання:

```
Користувач: "Висунь червоний кубик"
                    ↓
[Камера] → YOLO виявляє червоний кубик
                    ↓
[RL модель] → обчислює необхідні кути joints
                    ↓
[Arduino] → керує сервоприводами
                    ↓
[Роборука] → підіймає кубик 🎉
```

---

## 🔄 Як воно працює?

###架構 (Архітектура):

```
┌──────────────────────────────────────────────┐
│ 🖥️  ПК (Навчання)                            │
│ • PyBullet симуляція                         │
│ • PPO алгоритм (Proximal Policy Optimization)│
│ • 400+ GPU cores                             │
│ Результат: model.zip + model.tflite          │
└──────────────────┬───────────────────────────┘
                   │ (2-4 години навчання)
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────────┐ ┌─────▼──────────────┐
│ 🍊 Orange Pi PC    │ │ 🍊 Orange Pi Zero  │
│ (2GB RAM)          │ │ (512MB RAM)        │
│                    │ │                    │
│ • YOLO (TFLite)    │ │ • RL (TFLite)      │
│ • 30 FPS           │ │ • 20 Hz            │
│ • Камера           │ │ • Serial ↔ Arduino │
└─────┬──────────────┘ │ • MQTT subscribe   │
      │                └────────┬───────────┘
      │                         │
      └─────── MQTT ────────────┘
              (детекції)
                │
                ↓
┌──────────────────────────────────────────────┐
│ 📟 Arduino Mega 2560                         │
│ • PCA9685 servo driver                       │
│ • 6x Servo control (PWM)                     │
│ • Енкодери, кінцеві вимикачі                │
└──────────────────┬───────────────────────────┘
                   │ (PWM signals)
                   ↓
            🦾 Роборука
```

### Потоки даних:

```
НАВЧАННЯ (на ПК, один раз):
────────────────────────────
Robot State (angles, positions)
         ↓
    [RL Agent]
         ↓
    Action (new angles)
         ↓
PyBullet Simulation (forward dynamics)
         ↓
Reward (як близько до цілі?)
         ↓
PPO Algorithm оновлює ваги
         ↓
Повторити 500,000 разів

ЕКСПОРТ:
────────
PPO модель (PyTorch)
         ↓
TensorFlow конвертація
         ↓
TFLite квантизація (INT8)
         ↓
model.tflite (200KB) ← готово для Orange Pi


ВИКОНАННЯ (на Orange Pi, постійно):
───────────────────────────────────
[Камера] → Frame
         ↓
  [YOLO inference] → Детекція координат
         ↓
  [MQTT publish] → arm/vision/objects
         ↓
  [RL inference] → Нові кути
         ↓
  [Serial write] → JSON на Arduino
         ↓
  [Arduino] → PWM на сервоприводи
         ↓
  🦾 Роборука рухається
```

---

## ⚙️ Вимоги

### Hardware:

| Компонент | Де | Вимоги | Навіщо |
|-----------|-----|--------|---------|
| **ПК** | Для навчання | GPU (NVIDIA 4GB+), CPU (8+ cores), 16GB RAM | Швидке PPO навчання |
| **Orange Pi PC** | Постійно запущений | 2GB RAM, 4-core ARM | YOLO детекція 30 FPS |
| **Orange Pi Zero** | Постійно запущений | 512MB RAM, 1.2GHz ARM | RL inference 20 Hz |
| **Arduino Mega 2560** | Постійно запущений | 16MHz, 8KB RAM | Контроль моторів |
| **PCA9685** | На Arduino | I2C servo driver | 16x PWM каналів |
| **6x Servo** | Роборука | 3-5V, torque 10+ kg·cm | Приводи joints |
| **Logitech C170** | На Orange Pi PC | USB камера | Детекція об'єктів |

### Software:

**На ПК:**
- Ubuntu 20.04+ або Windows з WSL2
- Docker та docker-compose
- NVIDIA CUDA Toolkit (опціонально, але рекомендовано)
- Git

**На Orange Pi:**
- Armbian 25.8+ (Debian-based)
- Docker та docker-compose
- Python 3.9+

### Мережа:

- ПК та обидва Orange Pi в **одній локальній мережі** (WiFi або Ethernet)
- Мінімальна затримка: < 100ms для MQTT

---

## 📦 Встановлення

### Крок 1: Клонування репозиторію

**На ПК та обох Orange Pi:**

```bash
git clone https://github.com/your-org/opi-zero-stack.git
cd opi-zero-stack
```

### Крок 2: Структура директорій

```bash
# Переконатись, що структура корректна:
ls -la

# Мають бути:
# training/          # ПК: навчання
# yolo-detection/    # Orange Pi PC: детекція
# app/               # Orange Pi Zero: RL контроль
# firmware/          # Arduino код
# mosquitto/         # MQTT конфіг
# docker-compose.yml
# docker-compose.train.yml
# Makefile
```

### Крок 3: Встановлення Docker

**На ПК (Ubuntu):**
```bash
# Встановити Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Додати користувача в docker групу
sudo usermod -aG docker $USER
newgrp docker

# Встановити docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**На Orange Pi (Armbian):**
```bash
# Встановити Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker orangepi

# docker-compose вже в системі
docker compose --version
```

### Крок 4: Перевірка Arduino

**На Orange Pi Zero або ПК (якщо Arduino підключена через USB):**

```bash
# Перевірити, чи видна Arduino
ls -la /dev/serial/by-id/

# Має бути щось на кшталт:
# usb-Arduino__www.arduino.cc__0042_75735353937351610261-if00
```

Якщо не видна:
```bash
# Встановити драйвери
sudo apt install arduino-core

# Перезавантажитись
sudo reboot
```

### Крок 5: Камера на Orange Pi PC

```bash
# Перевірити камеру
ls -la /dev/v4l/by-id/

# Має бути щось на кшталт:
# usb-_Webcam_C170-video-index0
```

Якщо не видна:
```bash
# Встановити допоміжні пакети
sudo apt install v4l-utils

# Перезагрузити USB
sudo modprobe -r uvcvideo && sleep 2 && sudo modprobe uvcvideo

# Повторно перевірити
ls -la /dev/v4l/by-id/
```

---

## 🏋️ Навчання (ПК)

### 🖥️ Що запустити на ПК: Точна інструкція

**Три команди, які потрібні у більшості випадків:**

```bash
# 1. Навчання (2-4 години)
make train

# 2. Моніторинг (в іншому терміналі)
make tensorboard

# 3. Експорт (коли навчання готово)
make export
```

---

### Крок 0: Підготовка (один раз)

```bash
# Перейти в папку проекту
cd ~/opi-zero-stack

# Переконатись, що структура корректна
ls -la
# Має бути:
# training/
# Makefile
# docker-compose.train.yml
# README.md

# Перевірити Docker
docker --version
docker compose --version

# Перевірити GPU (якщо є NVIDIA)
nvidia-smi
# Має показати: GeForce GTX/RTX, CUDA version
```

---

### Крок 1: Запуск навчання

**Це займе 2-4 години!**

```bash
# Базовий запуск
make train

# Або вручну
docker compose -f docker-compose.train.yml up --build training

# Налаштування під ресурси через додаткові аргументи
make train ARGS="--n-envs 2 --batch-size 32"  # приклад для слабкої GPU
# або
make train -- --n-envs 8 --batch-size 128 --total-timesteps 1000000
```

Що відбувається:
1. **Збирання образу** (1-2 хвилини) – інсталюються залежності та симулятор.
2. **Ініціалізація** (≈30 сек) – піднімається PyBullet, завантажується середовище Gymnasium, створюється PPO агент.
3. **Навчання** (2-4 години) – у логах зʼявляються рядки на кшталт:
   ```
   Rollout: 10%| | 512/5000 [00:00<00:06, 668.77it/s]
   | explained_variance | 0.05 |
   | ep_rew_mean        | 12.3 |
   ```
4. **Збереження** – артефакти опиняються в `training/models/`.

**Як зупинити:** `Ctrl+C` у терміналі. Контейнер зупиниться, а проміжні дані залишаться у `training/models/`.

---

### Моніторинг прогресу

У **іншому терміналі** запустіть:

```bash
make tensorboard
```

TensorBoard працюватиме на `http://localhost:6006` та показує:
- 📈 **Episode Reward** – має зростати (0 → 50 → 100).
- 📉 **Policy Loss** – має спадати.
- 📊 **Value Loss** – стабільний, без сильних стрибків.

> ℹ️ Якщо TensorBoard не встановлено у вашому середовищі, запуск `make train` не впаде: скрипт вимкне логування
> та виведе повідомлення. Можна також вручну вимкнути логування прапорцем `--disable-tensorboard`.

---

### Крок 2: Контроль та стабільність

Під час навчання можна:
- ☕ Пити каву або стежити за графіками в TensorBoard.
- 🧪 Перевіряти, що Reward зростає. Якщо значення зависли на негативних, перезапустіть: `make clean` → `make train`.

---

### Крок 3: Експорт моделей

Коли вивід показує, що навчання завершено, виконайте:

```bash
make export
```

Або вручну:

```bash
docker compose -f docker-compose.train.yml run --rm training python export_models.py
```

> ℹ️ За замовчуванням використовується `training/models/ppo_model.zip`. Якщо у вас інший чекпойнт,
> передайте шлях через `--ppo-model`.

Результат у `training/models/`:
- `ppo_model.tflite` (≈200 KB) – для Orange Pi Zero.
- `yolov8n.tflite` (≈3 MB) – для Orange Pi PC.
- `ppo_model.zip` – повний чекпойнт для резервних копій або повторного експорту.

Перевірити файли:

```bash
ls -lh training/models/
```

---

### 🎯 Сценарії використання

**Сценарій 1: Перший запуск**
```bash
make train
make tensorboard  # у другому терміналі
```
**Результат:** натренована модель, графіки в TensorBoard, готовність до експорту.

**Сценарій 2: Поліпшення моделі**
```bash
make train ARGS="--total-timesteps 1000000 --policy-hidden-dims 256 256 --learning-rate 1e-4"
```

**Сценарій 3: Щось пішло не так**
```bash
make clean
make train
```

---

### ⚙️ Налаштування для ПК

- **Слабка GPU (<4GB):** `make train ARGS="--n-envs 2 --batch-size 32"`
- **Потужна машина (8GB+ GPU):** `make train ARGS="--n-envs 8 --batch-size 128 --total-timesteps 1000000"`
- **Без GPU (тільки CPU):** `make train` працює, але буде значно повільніше (20-30 годин).

---

### 🚀 Повторюваний workflow на ПК

- **День 1 (Встановлення):** встановити Docker, клонувати репозиторій, перевірити структуру (`ls -la training/`, `ls docker-compose.train.yml`).
- **День 2 (Навчання):** у першому терміналі `make train`, у другому `make tensorboard` і відкрити `http://localhost:6006`.
- **День 3 (Експорт та передача):** `make export`, перевірити артефакти в `training/models/`, скопіювати TFLite файли на Orange Pi за потреби.

---

### ⚠️ Частих помилок на ПК

- **docker: command not found** – встановіть Docker і повторіть `docker --version`.
- **Out of memory / CUDA out of memory** – зменште batch: `make train ARGS="--batch-size 32"`; за потреби очистіть ресурси Docker: `docker system prune -a`.
- **Permission denied при TensorBoard** – вирівняйте права: `sudo chown -R $USER:$USER training/`.
- **Сервіс завис** – перезберіть усе: `make clean` і `make train`.

---

### 💾 Резервні копії

```bash
# Архівувати після навчання
tar -czf model_backup_$(date +%Y%m%d).tar.gz training/models/ppo_model.zip

# Відновити при потребі
tar -xzf model_backup_*.tar.gz
make export  # оновити TFLite після відновлення
```
## 🍊 Розгортання (Orange Pi)

### Чому розділено?

| Пристрій | RAM | Завдання | Чому |
|----------|-----|----------|------|
| **Orange Pi PC** | 2GB | YOLO (30 FPS) | YOLO = 3MB модель, потребує більше RAM |
| **Orange Pi Zero** | 512MB | RL (20 Hz) | RL = 200KB, мала й легка |

### На Orange Pi PC (детекція):

#### Кроки:

1. **Копіювання YOLO моделі:**

```bash
# На ПК (де навчали):
scp training/models/yolov8n.tflite orangepi@192.168.1.100:~/opi-zero-stack/yolo-detection/models/

# Замінити 192.168.1.100 на IP Orange Pi PC
```

2. **Запуск YOLO сервісу:**

```bash
# На Orange Pi PC:
cd opi-zero-stack

# Збудувати образ
docker compose build yolo-detector

# Запустити
docker compose up -d yolo-detector

# Перевірити логи
docker compose logs -f yolo-detector
```

**Очікуваний вивід:**
```
🎥 YOLO TFLite Detector ініціалізовано
🚀 Детекція запущена
📷 3 об'єктів | Inference: 45.2ms
📷 2 об'єктів | Inference: 38.1ms
```

3. **Перевірка MQTT:**

```bash
# На Orange Pi PC (у іншому терміналі):
docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/vision/objects' -v

# Очікуваний вивід:
# arm/vision/objects {"timestamp": 1234567890, "objects": [{"x": 0.45, "y": 0.52, "confidence": 0.89}], "inference_time_ms": 45.2}
```

---

### 🍊 Orange Pi PC: Детальна інструкція

**Коротко:** `Камера → YOLO (30 FPS) → MQTT publish (arm/vision/objects)`

```text
Камера → YOLO (30 FPS) → MQTT publish
                         arm/vision/objects
                         {"x": 0.45, "y": 0.52, ...}
```

#### Крок 0: Перевірка обладнання

```bash
ssh orangepi@192.168.1.100    # пароль: orangepi (якщо не змінювали)
cat /etc/os-release           # Armbian 25.8 або Debian 12
ping 8.8.8.8                  # перевірити інтернет
ls -la /dev/v4l/by-id/        # камера має бути видна
```

Якщо камери немає:

```bash
sudo modprobe -r uvcvideo && sleep 2 && sudo modprobe uvcvideo
ls -la /dev/v4l/by-id/
```

#### Крок 1: Встановлення Docker

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo bash get-docker.sh
docker --version
sudo usermod -aG docker orangepi
sudo reboot
```

Після перезавантаження:

```bash
docker ps  # має працювати без sudo
```

#### Крок 2: Встановлення docker-compose

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker compose --version
```

#### Крок 3: Клонування проекту

```bash
cd ~
git clone https://github.com/your-org/opi-zero-stack.git
cd opi-zero-stack
ls -la                      # має бути yolo-detection/, app/, mosquitto/, docker-compose.yml
ls -la yolo-detection/
ls -la docker-compose.yml
```

#### Крок 4: Копіювання YOLO моделі

На ПК (де навчали):

```bash
ls -lh training/models/yolov8n.tflite  # ≈3MB
scp training/models/yolov8n.tflite orangepi@192.168.1.100:~/opi-zero-stack/yolo-detection/models/
```

На Orange Pi PC:

```bash
ls -la yolo-detection/models/  # -rw-r--r-- 3.1M yolov8n.tflite
```

#### Крок 5: Перевірка Mosquitto (MQTT брокер)

```bash
cat docker-compose.yml | grep -A 10 "mqtt:"
# mqtt:
#   image: eclipse-mosquitto:2
#   ports: ["1883:1883"]
```

#### Крок 6: Запуск MQTT + YOLO

```bash
pwd  # /home/orangepi/opi-zero-stack
docker compose up -d
docker compose ps
# mqtt            Up
# yolo-detector   Up
# mqttc           Up
```

Якщо помилка:

```bash
docker compose down
docker system prune -a
docker compose up -d --build
```

#### Крок 7: Перевірка логів YOLO

```bash
docker compose logs -f yolo-detector
# 🎥 YOLO TFLite Detector ініціалізовано
# 🚀 Детекція запущена
# 📷 3 об'єктів | Inference: 45.2ms
# 📷 2 об'єктів | Inference: 38.1ms
```

Помилка про камеру → перевірити `ls /dev/v4l/by-id/` або перезавантажити USB модуль (`sudo modprobe -r uvcvideo && sleep 2 && sudo modprobe uvcvideo`).

#### Крок 8: Перевірка MQTT публікацій

```bash
docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -v
# arm/vision/objects {"timestamp": 1732000000, "objects": [...], "inference_time_ms": 45.2}
```

#### Що зʼявляється на Orange Pi PC

```bash
docker compose ps
# eclipse-mosquitto:2  (MQTT)
# robotarm-yolo:latest (YOLO)
# alpine:3.20          (MQTT tools)

# MQTT конфіг: mosquitto/config/mosquitto.conf
# MQTT дані:  mosquitto/data/
# MQTT логи:  mosquitto/log/
# YOLO модель: yolo-detection/models/yolov8n.tflite
```

#### 🧪 Тестування на Orange Pi PC

```bash
# Тест 1: TFLite + модель
docker compose exec yolo-detector python -c "import tflite_runtime.interpreter as tflite; print('✅ TFLite runtime OK'); tflite.Interpreter(model_path='/detection/models/yolov8n.tflite'); print('✅ YOLO модель завантажена')"

# Тест 2: Камера
docker compose exec yolo-detector python -c "import cv2; cap = cv2.VideoCapture('/dev/video0'); print(f'✅ Камера відкрита: {cap.isOpened()}'); ret, frame = cap.read(); print(f'✅ Кадр прочитаний: {frame.shape}'); cap.release()"

# Тест 3: MQTT
docker compose exec mqttc mosquitto_pub -h mqtt -t "test/message" -m "Hello from Orange Pi PC"
docker compose exec mqttc mosquitto_sub -h mqtt -t "test/message"
```

#### 🚀 Повний workflow на Orange Pi PC

```bash
# День 1: Встановлення
ssh orangepi@192.168.1.100
curl -fsSL https://get.docker.com -o get-docker.sh
sudo bash get-docker.sh
sudo usermod -aG docker orangepi
sudo reboot
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
cd ~ && git clone https://github.com/your-org/opi-zero-stack.git && cd opi-zero-stack

# День 2: Копіювання моделей
scp training/models/yolov8n.tflite orangepi@192.168.1.100:~/opi-zero-stack/yolo-detection/models/
ls -la yolo-detection/models/

# День 3: Запуск
docker compose up -d
docker compose ps
docker compose logs -f yolo-detector
docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -v
```

#### ⚠️ Типові проблеми та рішення

- Docker не встановлюється → `sudo apt update && sudo apt install -y curl` та повторити інсталяцію.
- Камера не видна → `sudo reboot` або `sudo modprobe -r uvcvideo && sleep 2 && sudo modprobe uvcvideo`; додатково `sudo apt install -y v4l-utils && v4l2-ctl --list-devices`.
- YOLO падає з памʼяті → перезапустити контейнер або зменшити розмір кадру у `yolo-detection/yolo_detector.py` (320×240 → 160×120) та перебудувати образ (`docker compose build --no-cache yolo-detector`).
- MQTT не публікує → перевірити логи `docker compose logs mqtt`, перезапустити `docker compose restart mqtt`, пересвідчитись у темі `docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/vision/objects'`.
- Інференс >100ms → зменшити розміри входу (320×240 → 160×120), знизити FPS (30 → 15) або перезавантажити систему.

#### 🛠️ Налаштування

- **MQTT IP:** дізнатись IP `hostname -I` і за потреби вказати його на Orange Pi Zero (`MQTT_HOST` у `docker-compose.yml`).
- **Розміри зображення YOLO:** у `yolo-detection/yolo_detector.py` змінити `cv2.CAP_PROP_FRAME_WIDTH`/`HEIGHT` (менше = швидше).
- **Порт MQTT:** у `docker-compose.yml` секція `mqtt` → `ports: ["1883:1883"]` (можна змінити на інший).

#### 📊 Моніторинг Orange Pi PC

```bash
docker compose stats --no-stream  # CPU/пам'ять контейнерів
cat /sys/class/thermal/thermal_zone0/temp  # температура CPU (45000 = 45°C)
```

#### 🎯 Формат MQTT повідомлень

Тема: `arm/vision/objects`

```json
{
  "timestamp": 1732000000.123,
  "objects": [
    {"x": 0.45, "y": 0.52, "confidence": 0.89, "class": "cup"},
    {"x": 0.23, "y": 0.71, "confidence": 0.76, "class": "bottle"}
  ],
  "inference_time_ms": 45.2
}
```

**Checklist:** Docker встановлено, docker-compose працює, камера видна, модель скопійована (≈3MB), `docker compose ps` показує `mqtt`, `yolo-detector`, `mqttc`, логи YOLO йдуть, `mosquitto_sub` бачить повідомлення – Orange Pi PC готова.

### На Orange Pi Zero (RL контроль):

#### Кроки:

1. **Копіювання RL моделі:**

```bash
# На ПК (де навчали):
scp training/models/ppo_model.tflite orangepi@192.168.1.101:~/opi-zero-stack/app/model.tflite

# Замінити 192.168.1.101 на IP Orange Pi Zero
```

2. **Оновлення конфігурації:**

```bash
# На Orange Pi Zero:
cd opi-zero-stack/app

# Відредагувати docker-compose.yml
# Змінити DUMMY_MODEL="1" на DUMMY_MODEL="0"
```

3. **Запуск RL сервісу:**

```bash
# На Orange Pi Zero:
cd opi-zero-stack

# Збудувати образ
docker compose build app

# Запустити
docker compose up -d app

# Перевірити логи
docker compose logs -f app
```

**Очікуваний вивід:**
```
✅ RobotController ініціалізовано
✅ Model: /app/model.tflite
✅ Serial: /dev/ttyACM0
✅ MQTT connected
🚀 Control loop...
🔄 20.1Hz | YOLO: 0.89
```

4. **Перевірка здоров'я:**

```bash
# На Orange Pi Zero (або з ПК):
curl http://192.168.1.101:8000/healthz

# Очікуваний вивід:
# {"status":"ok","model_loaded":true,"serial_connected":true}
```

---

## 🚀 Запуск

### Повна інициалізація (перший раз):

**На ПК:**
```bash
# 1. Навчання (~3 години)
make train

# 2. Моніторинг (у іншому терміналі)
make tensorboard

# 3. Коли готово → експорт
make export
```

**На Orange Pi PC:**
```bash
# 4. Запуск YOLO
docker compose up -d yolo-detector
docker compose logs -f yolo-detector
```

**На Orange Pi Zero:**
```bash
# 5. Запуск RL
docker compose up -d app
docker compose logs -f app
```

**Перевірка:**
```bash
# На Orange Pi Zero:
make healthz
make test-predict
```

### Постійний запуск:

**На обох Orange Pi:**

```bash
# Запустити все
docker compose up -d

# Перевірити статус
docker compose ps

# Logи
docker compose logs -f

# Зупинити все
docker compose down
```

---

## 🔍 Діагностика

### Проблема 1: YOLO не запускається на Orange Pi PC

```bash
# Перевірити образ
docker image ls | grep yolo

# Перевірити логи
docker compose logs yolo-detector

# Якщо помилка про TFLite:
docker compose exec yolo-detector python -c "import tflite_runtime"

# Переібути образ
docker compose build --no-cache yolo-detector
```

### Проблема 2: RL не знаходить моделю на Orange Pi Zero

```bash
# Перевірити файл
ls -la app/model.tflite

# Має бути cerca 200KB
# Якщо немає:
scp training/models/ppo_model.tflite orangepi@192.168.1.101:~/opi-zero-stack/app/model.tflite

# Перезапустити
docker compose restart app
```

### Проблема 3: Arduino не відповідає

```bash
# На Orange Pi Zero:
# Перевірити підключення
ls -la /dev/serial/by-id/

# Перевірити логи app
docker compose logs app | grep Serial

# Якщо помилка NACK:
# 1. Перезавантажити Arduino: power off/on
# 2. Дати їй 2-3 сек на ініціалізацію
# 3. Перевірити прошивку в firmware/
```

### Проблема 4: MQTT публікація не видна

```bash
# Перевірити MQTT брокер
docker compose logs mqtt

# Перевірити підписку
docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -v

# Якщо не видно:
# 1. Перевірити IP Orange Pi PC та Zero (мають бути в одній мережі)
# 2. ping 192.168.1.100 з Orange Pi Zero
# 3. Перезапустити MQTT: docker compose restart mqtt
```

### Команди діагностики:

```bash
# Health check
make healthz

# MQTT моніторинг
make monitor

# API тест
make test-predict

# Читання стану
make test-state

# Логи
make logs-app
make logs-yolo
make logs-mqtt

# Shell доступ
make shell-app
make shell-yolo
```

---

## 📁 Структура проекту

```
opi-zero-stack/
│
├── 📁 training/                    🖥️ ПК: Навчання (тільки на ПК)
│   ├── Dockerfile
│   ├── requirements.txt             (PyTorch, TensorFlow, SB3)
│   ├── train_ppo.py                (PPO algorithm)
│   ├── export_models.py            (конвертація в TFLite)
│   ├── environments/
│   │   └── robot_arm_env.py        (Gymnasium env)
│   ├── models/
│   │   ├── ppo_model.zip           (PyTorch, 500MB, виходить тільки після train)
│   │   ├── ppo_model.tflite        (200KB, для Orange Pi Zero)
│   │   └── yolov8n.tflite          (3MB, для Orange Pi PC)
│   ├── tensorboard/                (TensorBoard логи)
│   └── logs/
│
├── 📁 yolo-detection/              🍊 Orange Pi PC: Детекція
│   ├── Dockerfile
│   ├── requirements.txt             (TFLite, OpenCV, MQTT)
│   ├── yolo_detector.py            (YOLO inference + MQTT)
│   └── models/
│       └── yolov8n.tflite          (скопіювати з training/)
│
├── 📁 app/                         🍊 Orange Pi Zero: RL контроль
│   ├── Dockerfile
│   ├── requirements.txt             (TFLite, Serial, MQTT, FastAPI)
│   ├── main.py                     (RL inference + Serial + MQTT)
│   └── model.tflite                (скопіювати з training/)
│
├── 📁 firmware/                    📟 Arduino: Motor control
│   ├── robotarm.ino                (Servo control, PCA9685, JSON parser)
│   └── README.md                   (як заливати на Arduino)
│
├── 📁 mosquitto/                   MQTT Broker
│   ├── config/                     (mosquitto.conf)
│   ├── data/                       (persistence data)
│   └── log/                        (broker logs)
│
├── docker-compose.yml              🐳 (MQTT + YOLO + RL)
├── docker-compose.train.yml        🐳 (Навчання на ПК)
├── Makefile                        📋 (Зручні команди)
└── README.md                       (цей файл)
```

### Про кожну папку:

**training/**
- Запускається тільки на ПК
- Тут відбувається PPO навчання (2-4 години)
- Результати: моделі в папці `models/`
- Після навчання моделі копіюються на Orange Pi

**yolo-detection/**
- Запускається на Orange Pi PC
- Читає з камери 30 FPS
- Запускає YOLO TFLite
- Публікує детекції в MQTT

**app/**
- Запускається на Orange Pi Zero
- Підписується на MQTT (детекції від YOLO)
- Запускає RL TFLite inference
- Відправляє команди на Arduino через Serial

**firmware/**
- Прошивка Arduino Mega
- Одноразово заливається на плату (не в Docker)
- Читає JSON команди з Serial
- Керує сервоприводами через PCA9685

**mosquitto/**
- MQTT брокер (як посередник між Orange Pi PC та Zero)
- Дозволяє їм комунікувати

---

## 🔑 Ключові команди

### На ПК:

```bash
make train          # Запуск навчання (2-4 год)
make tensorboard    # TensorBoard (http://localhost:6006)
make export         # Експорт моделей в TFLite
make clean          # Видалити все (осторожно!)
```

### На Orange Pi:

```bash
make up             # Запустити MQTT + YOLO + RL
make down           # Зупинити
make deploy         # Копіювання моделей з ПК
make logs-app       # Логи RL
make logs-yolo      # Логи YOLO
make monitor        # MQTT моніторинг
make test-predict   # API тест
make healthz        # Health check
```

---

## 📊 Метрики та що означають

### RL навчання (на ПК):

```
Episode Reward: -5.2
├─ Негативні значення = далеко від цілі
├─ 0 = справедливо
└─ 100+ = отримав цільовий об'єкт ✅

Policy Loss: 0.45
├─ Показує, як змінилась стратегія агента
└─ Менше = краще

Value Loss: 0.23
├─ Передбачення нагород
└─ Менше = краще прогнозування
```

### YOLO детекція (на Orange Pi PC):

```
Inference: 45.2ms
├─ Час на обробку одного кадру
├─ < 100ms для 30 FPS ✅
└─ ~ 33ms на кадр для гладкості

Objects: 3
├─ Кількість виявлених об'єктів
└─ Кожний має: x (гоз), y (верт), confidence (0-1)

Confidence: 0.89
├─ Впевненість моделі (0 = ганьба, 1 = впевнений)
└─ Типово > 0.5 для валідної детекції
```

### RL контроль (на Orange Pi Zero):

```
Freq: 20.1Hz
├─ 20 разів на секунду оновлюємо дії
├─ Потребно на швидку реакцію
└─ Оптимально 15-30 Hz

YOLO: 0.89
├─ Найновіша впевненість від YOLO
├─ 0 = об'єкт не видно
└─ > 0.5 = є ціль
```

---

## ⚡ Оптимізація та налаштування

### Якщо RL навчається дуже повільно:

```bash
cd training

# Відредагувати train_ppo.py
# Змінити параметри:
make train -- --n-envs 8        # більше parallelних環境ів
make train -- --batch-size 128  # більший batch
```

### Якщо YOLO запускається повільно на Orange Pi PC:

```bash
# У yolo-detection/yolo_detector.py
# Змінити розміри зображення:
frame.set(cv2.CAP_PROP_FRAME_WIDTH, 160)  # 320 → 160
frame.set(cv2.CAP_PROP_FRAME_HEIGHT, 120) # 240 → 120
# Меньше = швидше, але менше точності
```

### Якщо RL на Orange Pi Zero заїдає:

```bash
# У app/main.py
# Збільшити затримку циклу:
loop_time = 0.1  # 0.05 → 0.1 (10 Hz замість 20 Hz)
```

---

## 🤝 Про лікензію та благодарність

Цей проект використовує:
- **Stable-Baselines3** (MIT) - RL алгоритми
- **YOLOv8** (AGPL) - детекція об'єктів
- **PyBullet** (Zlib) - симуляція
- **TensorFlow Lite** (Apache 2.0) - мобільний inference
- **Docker** (Apache 2.0) - контейнеризація

---

## ❓ FAQ

**Q: Чому PPO, а не DQN?**
A: PPO стабільніше учиться і краще працює для неперервних дій (кути суглобів).

**Q: Чи можна додати більше сенсорів?**
A: Так! Додайте їх до observation space в `environments/robot_arm_env.py`.

**Q: Як дізнатися, коли модель достатньо навчена?**
A: Коли Episode Reward > 90 в TensorBoard і роборука консистентно хапає об'єкти.

**Q: Чи можна навчати на CPU?**
A: Технічно так, але це займе 20-30 годин замість 2-4. GPU дуже рекомендується.

**Q: Чи можна змінити архітектуру мережі?**
A: Так! У `train_ppo.py` змініть `policy_kwargs["net_arch"]` з `[128, 128]` на `[256, 256]` або `[64, 64]`.

**Q: Що робити, якщо Orange Pi Zero зависає?**
A: Перевірте `docker compose stats`. Якщо пам'ять 100%, зменшіть частоту контролю циклу в `app/main.py`.

**Q: Як експортувати новішу модель?**
A: Скопіюйте нову `ppo_model.zip` з `training/models/` та запустіть `make export`.

**Q: Чи потрібна мне розглядати PyBullet симуляцію?**
A: Ні, вона автоматична в контейнері. Просто дивіться TensorBoard.

**Q: Як додати нові об'єкти для розпізнавання?**
A: YOLO вже вміє розпізнавати 80+ об'єктів (людей, машин, кубиків тощо). Щоб додати новий - потрібен fine-tuning.

**Q: Чи можна запустити без камери для тестування?**
A: Так! Запустіть z `DUMMY_MODEL=1` для тестування логіки без моделей.

---

## 🎯 Типовий день роботи з системою

### День 1: Встановлення та запуск тесту

```bash
# Ранок: Клонування та перевірка
git clone https://github.com/your-org/opi-zero-stack.git
cd opi-zero-stack

# Перевірити Docker
docker --version
docker compose --version

# Перевірити Arduino та камеру
ls /dev/serial/by-id/
ls /dev/v4l/by-id/

# Полудень: Запуск тесту на Orange Pi
docker compose up -d
docker compose logs app
curl http://localhost:8000/healthz

# Вечір: Перевірити MQTT
docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -v
```

### День 2-5: Навчання на ПК

```bash
# Понеділок ранок: Запуск навчання
make train

# Весь день: Моніторинг в TensorBoard
make tensorboard
# Відкрити http://localhost:6006
# Перевірити, чи зростає Reward: 0 → 50 → 100

# П'ятниця вечір: Експорт моделей
make export
# ✅ ppo_model.tflite готова
# ✅ yolov8n.tflite готова
```

### День 6: Розгортання на Orange Pi

```bash
# Ранок: Копіювання моделей
scp training/models/*.tflite orangepi@192.168.1.100:~/opi-zero-stack/yolo-detection/models/
scp training/models/ppo_model.tflite orangepi@192.168.1.101:~/opi-zero-stack/app/model.tflite

# День: Запуск на Orange Pi PC та Zero
ssh orangepi@192.168.1.100
docker compose up -d yolo-detector
docker compose logs -f yolo-detector

ssh orangepi@192.168.1.101
docker compose up -d app
docker compose logs -f app

# Вечір: Тестування
make healthz
make test-predict
make monitor
```

### День 7: Налаштування та оптимізація

```bash
# Перевірити частоти та затримки
docker compose exec app python -c "import sys; print(sys.version_info)"

# Якщо все працює - готово! 🎉
# Роборука тепер може:
# ✅ Бачити об'єкти (YOLO)
# ✅ Вирішувати, як їх хопати (RL)
# ✅ Керувати сервоприводами (Arduino)
```

---

## 🏗️ Як розширити систему

### Додати нові сенсори

1. **Виміри відстані (LiDAR/Ultrasonic)**

```python
# У environments/robot_arm_env.py додати до observation:
additional_sensors = np.array([distance_to_object, force_on_gripper])
obs = np.concatenate([obs, additional_sensors])
```

2. **Переднавчити модель**

```bash
make train -- --total-timesteps 1000000
```

### Додати новий завдання

1. **Замість "підйому об'єкту" - "переміщення"**

```python
# У environments/robot_arm_env.py змініть _compute_reward():
def _compute_reward(self):
    # Замість: дистанція до об'єкту
    # Додайте: дистанція до цільової позиції
    target_world = np.array([0.3, 0.0, 0.15])  # фіксована позиція
    distance = np.linalg.norm(self._get_ee_pos() - target_world)
    return -distance * 10
```

2. **Переналітати**

```bash
make train -- --total-timesteps 200000  # менше часу для нового завдання
```

### Додати графічну візуалізацію

```bash
# Встановити на ПК:
pip install pygame matplotlib

# У training/train_ppo.py змініть:
env = make_vec_env(RobotArmEnv, n_envs=1, render_mode="human")
```

---

## 🐛 Типові помилки та як їх виправити

### Помилка 1: "No module named 'tflite_runtime'"

```bash
# На Orange Pi:
pip install tflite-runtime

# Або в Docker (уже включено в requirements.txt)
```

### Помилка 2: "MQTT connection refused"

```bash
# На Orange Pi:
docker compose up -d mqtt
docker compose logs mqtt

# Перевірити, чи слухає на порту 1883
docker compose exec mqtt ss -lntp | grep 1883
```

### Помилка 3: "Serial port: Permission denied"

```bash
# На Orange Pi Zero:
sudo usermod -aG dialout orangepi
# Перезавантажитися
sudo reboot
```

### Помилка 4: "Arduino не відповідає (NACK)"

```bash
# 1. Перевірити Arduino скетч в firmware/
# 2. Перезавантажити Arduino (відключити/підключити)
# 3. Дати 2-3 сек на ініціалізацію
# 4. Перевірити baud rate: 115200

# Тестувати з Serial Monitor в Arduino IDE
```

### Помилка 5: "YOLO inference дуже повільна"

```bash
# На Orange Pi PC перевірити:
docker compose exec yolo-detector python -c "import cv2; print(cv2.getTickCount())"

# Якщо < 10M тиків/сек - проблема з CPU
# Рішення: змалити розмір зображення до 160x120
```

---

## 📈 Як моніторити в реальному часі

### Встановити Prometheus + Grafana (опціонально)

```bash
# На ПК (якщо потрібна централізована статистика):
docker run -d -p 9090:9090 prom/prometheus
docker run -d -p 3000:3000 grafana/grafana

# Конфігурація:
# Prometheus datasource: http://localhost:9090
# Dashboard: System Performance
```

### Простий shell моніторинг

```bash
# На Orange Pi Zero
watch -n 1 'docker stats --no-stream'

# Або
while true; do 
  curl -s http://localhost:8000/metrics | python -m json.tool
  sleep 1
done

# На Orange Pi PC
docker compose exec yolo-detector ps aux
free -m
```

---

## 🔐 Безпека

### Захист від невалідних команд

```python
# У app/main.py вже є перевірка:
if action < -np.pi or action > np.pi:
    logger.warning("Action out of bounds!")
    action = np.clip(action, -np.pi, np.pi)
```

### Watchdog таймер

```python
# Якщо немає MQTT message > 2 сек:
if time.time() - last_mqtt_time > 2.0:
    stop_all_motors()
    logger.error("MQTT timeout!")
```

### Emergency stop

```bash
# Натиснути Ctrl+C в терміналі з логами:
# Все зупиниться і сохранит стан
docker compose down
```

---

## 🌐 Розгортання на кількох робо-руках

Якщо у вас кілька однакових установок:

```bash
# 1. Клонувати цей проект на кожний Orange Pi
git clone https://github.com/your-org/opi-zero-stack.git

# 2. Zmінити MQTT topics за їх імена:
# На Orange Pi #1: arm1/vision/objects, arm1/command
# На Orange Pi #2: arm2/vision/objects, arm2/command

# 3. Змініть в app/main.py та yolo_detector.py:
MQTT_TOPIC_PREFIX = os.getenv("ROBOT_NAME", "arm1")

# 4. Запустити з різними імена:
ROBOT_NAME=arm1 docker compose up -d
ROBOT_NAME=arm2 docker compose up -d
```

---

## 📚 Освітні матеріали

### Що це за алгоритм - PPO?

PPO (Proximal Policy Optimization) - це метод машинного навчання, де агент:
1. Спостерігає стан (кути joints, позиція об'єкту)
2. Приймає дію (нові кути)
3. Отримує винагороду (близько до цілі = висока винагорода)
4. Оновлює мозок, щоб подібні ситуації давали кращі дії
5. Повторює мільйон разів

### Що таке YOLO?

YOLO (You Only Look Once) - це нейронна мережа для детекції об'єктів:
1. Отримує зображення з камери
2. За один прохід аналізує весь образ
3. Знаходить координати об'єктів та їх категорії
4. Виводить: [(x, y, class, confidence), ...]

### Як вони працюють разом?

```
[Камера] → [YOLO] → "Червоний кубик на (0.45, 0.52)"
                              ↓
                        [RL Policy]
                              ↓
            "Щоб його схопити, потрібні кути:
             joint1=45°, joint2=90°, ..."
                              ↓
                        [Arduino]
                              ↓
                    🦾 Роборука рухається!
```

---

## ✨ Що далі?

### Фаза 2: Додати силомір

```python
# У firmware/robotarm.ino:
analogRead(A0)  # читання сили на захоплювачі
```

### Фаза 3: Мультизадачність

```python
# Натренувати одну модель для:
# - Підйому об'єктів
# - Їх переміщення
# - Їх укладання в коробку
```

### Фаза 4: Real-to-sim transfer

```python
# Імпортувати реальні дані в PyBullet
# Оновити симуляцію з реальною динамікою
```

---

## 🆘 Техпідтримка

### Якщо щось не працює:

1. **Перевірте логи:**
   ```bash
   docker compose logs -f app
   docker compose logs -f yolo-detector
   docker compose logs -f mqtt
   ```

2. **Перевірте health:**
   ```bash
   curl http://localhost:8000/healthz
   docker compose ps
   ```

3. **Перевірте мережу:**
   ```bash
   ping 192.168.1.100  # Orange Pi PC
   ping 192.168.1.101  # Orange Pi Zero
   ```

4. **Переібудуйте контейнери:**
   ```bash
   docker compose down
   docker system prune -a
   docker compose up --build -d
   ```

5. **Читайте лог файли:**
   ```bash
   docker compose logs mqtt | tail -50
   docker compose logs app | tail -50
   docker compose logs yolo-detector | tail -50
   ```

---

## 📞 Контакти та покупка

- **Документація**: [GitHub Wiki](https://github.com/your-org/opi-zero-stack/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-org/opi-zero-stack/issues)
- **Email**: support@robotarm.local

---

## 📝 Версійність

| Версія | Дата | Зміни |
|--------|------|-------|
| 1.0 | 2024-11-21 | ✅ Вперше релізована |

---

## 🎉 Вітаємо!

Якщо ви дочитали до цього місця - ви готові запустити систему! 

**Перші кроки:**
1. ✅ Запустіть `make train` на ПК
2. ✅ Чекайте TensorBoard графіків
3. ✅ Запустіть `make export` 
4. ✅ Розгорніть на Orange Pi
5. ✅ Дивіться, як ваша роборука вчиться! 🦾

**Успіхів! 🚀**

---

**Останнє оновлення**: 2024-11-21
**Версія**: 1.0
**Статус**: Готово до виробництва ✅
