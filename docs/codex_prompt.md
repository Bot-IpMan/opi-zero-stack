# 🤖 Промт для Codex: Robot Arm RL + YOLO + LLM Control

## 📋 Огляд проекту

Створити систему керування 6-DOF роботизованою рукою з використанням:
- **Reinforcement Learning (PPO)** для контролю
- **YOLO** для детекції об'єктів з камери
- **LLM (Claude/GPT)** для природномовного керування
- **MQTT** для комунікації між компонентами
- **Docker Compose** для всієї інфраструктури

## 🏗️ Архітектура системи

```
ПК (для навчання, один раз):
└── training/
    ├── train_ppo.py         # PPO навчання в PyBullet
    ├── robot_arm_env.py     # Gymnasium environment
    ├── export_models.py     # Конвертація в ONNX/TFLite
    └── robot_arm.urdf       # 6-DOF модель

ПК (для керування, опціонально):
└── llm-control/
    └── llm_controller.py    # LLM → HTTP команди

Orange Pi Zero (512MB RAM, ARMv7):
├── yolo-detection/
│   └── yolo_detector.py     # Камера → детекція → MQTT
├── app/
│   └── main.py              # MQTT → RL inference → Arduino
└── docker-compose.yml       # Все разом

Arduino Mega 2560:
└── firmware/
    └── robotarm.ino         # Serial JSON → PWM моторів
```

## ✅ Критичні вимоги (ОБОВ'ЯЗКОВО перевірити)

### 1. Hardware обмеження

**Orange Pi Zero:**
- ✅ RAM: 512MB - модель ≤ 200KB (TFLite INT8)
- ✅ CPU: ARMv7 1.2GHz - inference < 50ms
- ✅ Без AVX2/SSE4.1 - тільки ARM-сумісні пакети
- ❌ НЕ компілювати numpy/opencv з нуля (займе години і не вдасться)

**ПК для навчання:**
- ✅ Без SSE4.1 (AMD Phenom II X4 955) - PyTorch 1.13.1, НЕ TensorFlow 2.15
- ✅ Використати ONNX замість TFLite для експорту
- ✅ CPU-only навчання (2-4 години для 500K timesteps)

### 2. Package версії (КРИТИЧНО!)

**Training (ПК):**
```
torch==1.13.1                    # ✅ Без SSE4.1
torchvision==0.14.1
stable-baselines3[extra]==2.2.1
gymnasium==0.29.1
pybullet==3.2.6
numpy==1.24.3                    # ✅ Не 1.19.3!
onnx==1.14.0                     # Замість TensorFlow
onnxruntime==1.16.0
tensorboard==2.15.1
```

**YOLO Detection (Orange Pi Zero):**
```
opencv-python-headless==4.8.1.78  # ✅ Без GUI, швидше
numpy==1.24.3
paho-mqtt>=1.6.1,<2.0
tflite-runtime==2.14.0            # ✅ Не повний TensorFlow!
pillow==10.1.0
```

**App (Orange Pi Zero):**
```
fastapi==0.109.0
uvicorn==0.27.0
tflite-runtime==2.14.0            # ✅ Не TensorFlow!
numpy==1.24.3
paho-mqtt>=1.6.1,<2.0
pyserial==3.5
```

### 3. Dockerfile для Orange Pi (ARMv7)

**КРИТИЧНО - системні пакети для Debian 12+:**

```dockerfile
# training/Dockerfile - ПК (навчання)
FROM python:3.10-slim
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "train_ppo.py"]
```

```dockerfile
# yolo-detection/Dockerfile - Orange Pi Zero
FROM python:3.10-slim
RUN apt-get update && apt-get install -y \
    libgl1 \                    # ✅ Замість libgl1-mesa-glx
    libglib2.0-0t64 \          # ✅ Замість libglib2.0-0
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libopenblas0 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "yolo_detector.py"]
```

```dockerfile
# app/Dockerfile - Orange Pi Zero
FROM python:3.10-slim
RUN apt-get update && apt-get install -y \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]
```

**❌ НЕПРАВИЛЬНО (старі Debian 11 пакети):**
```dockerfile
RUN apt-get install -y libgl1-mesa-glx libglib2.0-0
# Ці пакети немає в Debian 12+!
```

### 4. Docker Compose структура

**Orange Pi Zero - docker-compose.yml:**

```yaml
services:
  mqtt:
    image: eclipse-mosquitto:2
    ports: ["1883:1883"]
    # КРИТИЧНО: persistent storage
    volumes:
      - ./mosquitto/config:/mosquitto/config:ro
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log

  yolo-detector:
    build: ./yolo-detection
    depends_on: [mqtt]
    environment:
      DUMMY_DETECTIONS: "1"  # Поки немає YOLO моделі
      MQTT_HOST: mqtt
      CAMERA_INDEX: "0"
    devices:
      - "/dev/video0:/dev/video0"  # Камера
    mem_limit: "200m"  # КРИТИЧНО для 512MB

  app:
    build: ./app
    depends_on: [mqtt, yolo-detector]
    environment:
      DUMMY_MODEL: "0"  # ✅ Реальна модель
      MQTT_HOST: mqtt
      SERIAL_DEV: /dev/ttyACM0
    devices:
      - "/dev/serial/by-id/usb-Arduino*:/dev/ttyACM0"
    ports: ["8000:8000"]
    mem_limit: "120m"  # КРИТИЧНО
```

## 🔍 Checklist перед запуском

### На ПК (навчання):

```bash
# 1. Перевірка CPU flags
cat /proc/cpuinfo | grep flags | grep sse4_1
# Якщо пусто → використати PyTorch 1.13.1

# 2. Dockerfile правильний
cat training/Dockerfile | grep "FROM python"
# Має бути: FROM python:3.10-slim

# 3. Правильні пакети
cat training/requirements.txt | grep torch
# Має бути: torch==1.13.1 (НЕ 2.1.0!)

# 4. URDF існує
ls -la training/robot_arm.urdf
# Має бути файл ~10KB

# 5. Environment правильний
cat training/environments/robot_arm_env.py | grep "def reset"
# Має бути метод reset() з try/except

# 6. Запуск навчання
docker compose -f docker-compose.train.yml up training
# Очікувати: "🚀 Starting PPO training..."
# Очікувати: "ep_rew_mean: 200+" (добре!)
# НЕ очікувати: "exit code 132" (SSE4.1 помилка!)

# 7. Експорт моделі
docker compose -f docker-compose.train.yml run training python export_models.py \
  --ppo-model models/ppo_model.zip \
  --output model.onnx
# Результат: model.onnx (~150KB)
```

### На Orange Pi Zero (розгортання):

```bash
# 1. Перевірка камери
ls -la /dev/v4l/by-id/
# Має бути: usb-_Webcam_C170-video-index0

# 2. Перевірка Arduino
ls -la /dev/serial/by-id/
# Має бути: usb-Arduino__www.arduino.cc__*

# 3. Перевірка моделі
ls -lh app/model.tflite
# Має бути: ~200KB (якщо більше 500KB - проблема!)

# 4. Dockerfile правильний
cat yolo-detection/Dockerfile | grep libglib
# Має бути: libglib2.0-0t64 (НЕ libglib2.0-0!)

# 5. Docker збірка без помилок
docker compose build
# НЕ має бути: "Package libgl1-mesa-glx has no installation candidate"
# НЕ має бути: "Installing build dependencies: still running..." (>5 хв)

# 6. Запуск
docker compose up -d
docker compose ps
# Всі сервіси: "Up"

# 7. Логи без помилок
docker compose logs yolo-detector | grep -i error
docker compose logs app | grep -i error
# Має бути порожньо або тільки warnings

# 8. Health check
curl http://localhost:8000/healthz
# Має бути: {"status":"ok","model_loaded":true,...}

# 9. MQTT працює
docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -v
# Має бути: arm/vision/objects {...}
```

## 🚨 Типові помилки та фікси

### Помилка 1: "exit code 132" (Illegal instruction)

**Причина:** CPU не підтримує SSE4.1/AVX2

**Фікс:**
```dockerfile
# training/requirements.txt
torch==1.13.1  # Замість 2.1.0
```

### Помилка 2: "Package libgl1-mesa-glx has no installation candidate"

**Причина:** Debian 12+ не має старих пакетів

**Фікс:**
```dockerfile
# Dockerfile
RUN apt-get install -y \
    libgl1 \                    # Замість libgl1-mesa-glx
    libglib2.0-0t64 \          # Замість libglib2.0-0
    libgomp1
```

### Помилка 3: "Installing build dependencies: still running..."

**Причина:** OpenCV компілюється з нуля (години!)

**Фікс:**
```txt
# requirements.txt
opencv-python-headless==4.8.1.78  # Замість opencv-python
```

### Помилка 4: "Out of memory" на Orange Pi Zero

**Причина:** Модель/образ завеликий

**Фікс:**
```yaml
# docker-compose.yml
services:
  app:
    mem_limit: "120m"  # Жорсткий ліміт
```

### Помилка 5: "Joint index out-of-range" в PyBullet

**Причина:** URDF не має 6 joints

**Фікс:**
```python
# robot_arm_env.py
num_joints = p.getNumJoints(self.robot_id)
for joint_id in range(min(6, num_joints)):  # ✅ Не більше існуючих!
    p.resetJointState(...)
```

### Помилка 6: "ep_rew_mean: -1000" (навчання не працює)

**Причина:** Погана функція винагороди

**Фікс:**
```python
# robot_arm_env.py
def _compute_reward(self):
    distance = np.linalg.norm(ee_pos - target_pos)
    distance = np.clip(distance, 0, 1.0)  # ✅ Клипування!
    
    reward = (1.0 - distance)  # ✅ Від 0 до 1
    if distance < 0.05:
        reward += 10.0  # ✅ Бонус
    
    return np.clip(reward, -50, 100)  # ✅ Обмеження
```

### Помилка 7: "MQTT connection refused"

**Причина:** MQTT брокер не запущений або не слухає

**Фікс:**
```bash
# На Orange Pi Zero
docker compose up -d mqtt
docker compose logs mqtt

# Перевірити, чи слухає на порту 1883
docker compose exec mqtt ss -lntp | grep 1883
```

### Помилка 8: "No module named 'tflite_runtime'"

**Причина:** TFLite runtime не встановлено

**Фікс:**
```bash
# На Orange Pi Zero
pip install tflite-runtime

# Або в requirements.txt
pip install tflite-runtime==2.14.0
```

### Помилка 9: "ModuleNotFoundError: No module named 'torch'"

**Причина:** PyTorch неправильної версії або не встановлено

**Фікс:**
```bash
# На ПК - перевірити версію
pip list | grep torch
# Має бути: torch==1.13.1

# Якщо неправильна, переінсталюйте:
pip uninstall torch torchvision -y
pip install torch==1.13.1 torchvision==0.14.1
```

### Помилка 10: "Serial port not found" або "Permission denied"

**Причина:** Arduino не підключена або немає прав

**Фікс:**
```bash
# Перевірити, чи видна Arduino
ls -la /dev/serial/by-id/
# Має бути: usb-Arduino__www.arduino.cc__*

# Додати користувача в dialout групу (Orange Pi)
sudo usermod -aG dialout orangepi
sudo usermod -aG dialout $USER

# Перезавантажити сеанс або:
newgrp dialout
```

## 📊 Критерії успіху

### Навчання (ПК):
- ✅ `ep_rew_mean` зростає: -100 → 0 → 50 → 150+
- ✅ `explained_variance` > 0.8
- ✅ TensorBoard показує збіжність
- ✅ Модель експортується < 500KB

### Розгортання (Orange Pi):
- ✅ YOLO inference < 100ms
- ✅ RL inference < 50ms
- ✅ Control loop > 10 Hz
- ✅ Serial ACK від Arduino
- ✅ MQTT публікує 20+ msg/sec

### Інтеграція:
- ✅ `curl http://192.168.1.101:8000/healthz` → 200 OK
- ✅ `docker compose ps` → всі "Up"
- ✅ Arduino відповідає "ACK"
- ✅ Роборука рухається ✅

## 🎯 Фінальна перевірка

```bash
# На ПК
cd ~/opi-zero-stack
ls -la training/models/model.onnx  # ~150KB ✅

# На Orange Pi Zero
docker compose up -d
sleep 10
curl http://localhost:8000/healthz | jq
# {"status":"ok","model_loaded":true,"serial_connected":true} ✅

docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -c 10
# arm/vision/objects {...} (10 повідомлень) ✅

curl -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"x":[0,0,0,0,0,0,0.5,0.5,0.9]}' | jq
# {"action":[...],"serial_ack":"ACK"} ✅
```

## 📝 Додаткові нотатки

1. **Ніколи не компілюйте пакети на Orange Pi** - тільки wheels!
2. **Завжди використовуйте `mem_limit`** в docker-compose
3. **TensorFlow НЕ підтримує старі CPU** - використати PyTorch/ONNX
4. **Debian 12+ змінила імена пакетів** - оновити Dockerfile
5. **Orange Pi Zero = 512MB** - модель + всі сервіси < 400MB

## ✅ Готово до розгортання якщо:

- [ ] Всі Dockerfile збираються < 5 хвилин
- [ ] Навчання досягає reward > 100
- [ ] Модель < 500KB
- [ ] Orange Pi Zero запускає всі сервіси
- [ ] Health check повертає OK
- [ ] MQTT публікує дані
- [ ] Arduino відповідає ACK
- [ ] Роборука рухається

**Якщо ВСІ чекбокси ✅ - система готова!** 🎉

---

## 🏗️ Розширення системи

### Додати нові сенсори

1. **Виміри відстані (LiDAR/Ultrasonic)**

```python
# У environments/robot_arm_env.py додати до observation:
additional_sensors = np.array([distance_to_object, force_on_gripper])
obs = np.concatenate([obs, additional_sensors])
```

2. **Переналітати модель**

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

## 🔗 Інтеграція з LLM (опціонально)

Якщо хочете додати природномовний контроль:

```python
# llm-control/llm_controller.py (на ПК)
import requests

def send_command(text_command):
    """Надіслати команду на Orange Pi Zero"""
    response = requests.post(
        "http://192.168.1.101:8000/command",
        json={"command": text_command}
    )
    return response.json()

# Приклад: "Висунь червоний кубик"
result = send_command("Lift red cube")
# → RL модель обчислює необхідні кути
# → Arduino керує сервоприводами
```

---

## 🔄 Потік розвитку

### Фаза 1: Базова система ✅ (поточна)
- [x] PPO навчання
- [x] YOLO детекція
- [x] MQTT комунікація
- [x] Arduino контроль

### Фаза 2: Сенсори (наступна)
- [ ] Силомір (grip force)
- [ ] IMU (орієнтація)
- [ ] Camera в реальному часі

### Фаза 3: Multi-task learning
- [ ] Одна модель для 5+ завдань
- [ ] Transfer learning з симуляції

### Фаза 4: Real-to-sim transfer
- [ ] Дані з реальної роборуки
- [ ] Оновлення симуляції

---

## 📊 Метрики для моніторингу

| Метрика | Де | Норма | Проблема |
|---------|-----|-------|----------|
| `ep_rew_mean` | TensorBoard | > 100 | < 0 = модель не учиться |
| `policy_loss` | TensorBoard | спадає | зростає = нестабільність |
| YOLO FPS | Docker logs | 20-25 | < 10 = занадто повільно |
| RL Hz | Docker logs | 20 | < 5 = контроль повільний |
| Serial ACK | Docker logs | OK | NACK = Arduino не відповідає |
| RAM usage | `docker stats` | < 400MB | > 450MB = перевантаження |

---

## 🆘 Отримання допомоги

### Збір логів для діагностики

```bash
# На ПК (навчання)
docker compose -f docker-compose.train.yml logs training > training.log
docker compose -f docker-compose.train.yml logs > full_training.log

# На Orange Pi Zero
docker compose logs > full_deployment.log
docker compose logs app > app.log
docker compose logs yolo-detector > yolo.log
docker compose logs mqtt > mqtt.log
```

### Типові запитання розробників

**Q: Чому модель експортується в ONNX, а не TFLite?**
A: Тому що на ПК uden CPU без SSE4.1, а TensorFlow не компілюється. ONNX + TFLite на Orange Pi.

**Q: Чи можна використовувати GPU на ПК?**
A: Так! PyTorch автоматично використовуватиме CUDA, якщо доступна. Навчання буде 5-10x швидше.

**Q: Навіщо так багато mem_limit обмежень?**
A: Orange Pi Zero має тільки 512MB. Без обмежень контейнери захоплюють всю пам'ять і система зависає.

**Q: Як дізнатися, коли модель достатньо навчена?**
A: Коли `ep_rew_mean` > 90-100 і роборука консистентно схоплює об'єкти 8-9 разів з 10.

**Q: Чи можна запустити все на одному ПК без Orange Pi?**
A: Теоретично так, але немає сенсу - роботизована рука неживого мозку!

---

## 📚 Посилання на інші ресурси

- [Stable-Baselines3 документація](https://stable-baselines3.readthedocs.io/)
- [Gymnasium (раніше OpenAI Gym)](https://gymnasium.farama.org/)
- [PyBullet документація](https://docs.google.com/document/d/10sXEhzFRSnvFcl3XxNGhnD4N2SedqwsuQhlulEsHbaE/)
- [YOLO v8](https://github.com/ultralytics/ultralytics)
- [TensorFlow Lite](https://www.tensorflow.org/lite)
- [Docker документація](https://docs.docker.com/)
- [MQTT стандарт](https://mqtt.org/)

---

**Останнє оновлення**: 2024-12-06  
**Версія**: 1.1  
**Статус**: Повна документація для розробників ✅
