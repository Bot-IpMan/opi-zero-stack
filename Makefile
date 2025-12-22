.DEFAULT_GOAL := help
.RECIPEPREFIX := >

# Colors
BOLD=\033[1m
BLUE=\033[1;34m
YELLOW=\033[1;33m
GREEN=\033[1;32m
RESET=\033[0m

.PHONY: help pc-build pc-up pc-logs pc-shell pc-down pc-train pc-export pc-deploy \
        opi-prepare opi-fix-requirements opi-fix-compose opi-build opi-up opi-logs opi-shell opi-down opi-health \
        health-all monitor-mqtt test-connection deploy-pc deploy-opi start logs monitor test-camera fix-camera train dashboard stop-all

help:
> @echo "${BOLD}Доступні команди:${RESET}"
> @echo "  ${BLUE}make pc-build${RESET}        - Збудувати LLM сервіс для ПК"
> @echo "  ${BLUE}make pc-up${RESET}           - Запустити сервіси ПК у фоні"
> @echo "  ${BLUE}make pc-logs${RESET}         - Потокові логи ПК сервісів"
> @echo "  ${BLUE}make pc-shell${RESET}        - Відкрити shell у контейнері ПК"
> @echo "  ${BLUE}make pc-down${RESET}        - Зупинити та видалити сервіси ПК"
> @echo "  ${BLUE}make pc-train${RESET}        - Навчання PPO на ПК"
> @echo "  ${BLUE}make pc-export${RESET}       - Експорт PPO моделі в TFLite"
> @echo "  ${BLUE}make pc-deploy${RESET}       - Копіювання моделі на Orange Pi Zero"
> @echo "  ${YELLOW}make opi-prepare${RESET}     - Підготовка Orange Pi (swap, очистка)"
> @echo "  ${YELLOW}make opi-fix-requirements${RESET} - Виправити версію OpenCV у requirements"
> @echo "  ${YELLOW}make opi-fix-compose${RESET} - Видалити версію з docker-compose"
> @echo "  ${YELLOW}make opi-build${RESET}       - Збудувати сервіс Orange Pi Zero"
> @echo "  ${YELLOW}make opi-up${RESET}          - Запустити сервіси Orange Pi у фоні"
> @echo "  ${YELLOW}make opi-logs${RESET}        - Потокові логи сервісів Orange Pi"
> @echo "  ${YELLOW}make opi-shell${RESET}       - Відкрити shell у контейнері Orange Pi"
> @echo "  ${YELLOW}make opi-down${RESET}        - Зупинка та видалення сервісів Orange Pi"
> @echo "  ${YELLOW}make opi-health${RESET}      - Health check сервісу Orange Pi"
> @echo "  ${GREEN}make health-all${RESET}      - Перевірка стану всіх сервісів"
> @echo "  ${GREEN}make monitor-mqtt${RESET}    - Моніторинг топіку greenhouse/# через MQTT"
> @echo "  ${GREEN}make test-connection${RESET} - Тест з'єднання між ПК та Orange Pi"
> @echo "  ${BLUE}make start${RESET}           - Запуск всіх сервісів у фоні"
> @echo "  ${BLUE}make logs${RESET}            - Потокові логи всіх сервісів"
> @echo "  ${BLUE}make stop-all${RESET}        - Зупинити всі ПК та Orange Pi сервіси"
> @echo "  ${GREEN}make monitor${RESET}         - Моніторинг топіків arm/# через MQTT"
> @echo "  ${YELLOW}make test-camera${RESET}      - Зберегти знімок та показати налаштування камери"
> @echo "  ${YELLOW}make fix-camera${RESET}       - Встановити експозицію, яскравість та gain"
> @echo "  ${YELLOW}make train${RESET}            - Запустити навчання роборуки"
> @echo "  ${GREEN}make dashboard${RESET}       - Запустити локальний dashboard на 8888"
> @echo "  ${BLUE}make deploy-pc${RESET}        - Розгортання сервісів на ПК"
> @echo "  ${YELLOW}make deploy-opi${RESET}       - Розгортання сервісів на Orange Pi"

# ПК
pc-build:
> @echo "${BLUE}[PC] Збірка LLM сервісу...${RESET}"
> docker compose -f docker-compose.pc.yml build

pc-up:
> @echo "${BLUE}[PC] Запуск сервісів ПК...${RESET}"
> @CAM_DEV="$${CAMERA_DEVICE:-/dev/video0}"; \
>         if [ -e "$$CAM_DEV" ]; then \
>                 echo "${BLUE}[PC] Камера виявлена ($$CAM_DEV). Проброшуємо пристрій...${RESET}"; \
>                 docker compose -f docker-compose.pc.yml -f docker-compose.pc.camera.yml up -d; \
>         else \
>                 docker compose -f docker-compose.pc.yml up -d; \
>         fi

pc-logs:
> @echo "${BLUE}[PC] Потокові логи ПК...${RESET}"
> docker compose -f docker-compose.pc.yml logs -f

pc-shell:
> @echo "${BLUE}[PC] Shell у контейнері pc-llm...${RESET}"
> docker compose -f docker-compose.pc.yml exec pc-llm-service /bin/bash

pc-down:
> @echo "${BLUE}[PC] Зупинка сервісів ПК та очищення контейнерів...${RESET}"
> docker compose -f docker-compose.pc.yml -f docker-compose.pc.camera.yml down

pc-train:
> @echo "🖥️ ПК: Запуск PPO навчання..."
> @echo "   ⏱️  Час: 2-4 години (залежить від GPU)"
> cd training && python train_ppo.py --total-timesteps 500000

pc-export:
> @echo "🖥️ ПК: Експорт моделі в TFLite..."
> cd training && python export_models.py \
>         --ppo-model models/final_model.zip \
>         --ppo-output models/ppo_model.tflite
> @echo "✅ Модель готова в training/models/ppo_model.tflite"

pc-deploy:
> @echo "🖥️ ПК: Копіювання моделі на Orange Pi Zero..."
> @read -p "Введіть IP Orange Pi Zero (192.168.1.101): " IP; \
>         scp training/models/ppo_model.tflite orangepi@$$IP:~/opi-zero-stack/app/model.tflite
> @echo "✅ Модель скопійована"

# Orange Pi Zero
opi-prepare:
> @echo "🍊 Orange Pi Zero: Підготовка..."
> @sudo swapoff -a 2>/dev/null || true
> @sudo fallocate -l 2G /swapfile
> @sudo chmod 600 /swapfile
> @sudo mkswap /swapfile
> @sudo swapon /swapfile
> @echo "✅ Swap 2GB ввімкнутий"
> @free -h | grep -i swap
> @docker compose -f docker-compose.orangepi.yml down
> @docker system prune -a -f

opi-fix-requirements:
> @echo "🍊 Orange Pi Zero: Виправлення requirements.txt..."
> @sed -i 's/opencv-python-headless==4.10.0.84/opencv-python-headless==4.8.0.76/' app/requirements.txt
> @grep opencv app/requirements.txt
> @echo "✅ OpenCV версія змінена"

opi-fix-compose:
> @echo "🍊 Orange Pi Zero: Видалення застарілої версії з docker-compose..."
> @sed -i '/^version:/d' docker-compose.orangepi.yml
> @echo "✅ Виправлено docker-compose.orangepi.yml"

opi-build: opi-prepare opi-fix-requirements opi-fix-compose
> @echo "🍊 Orange Pi Zero: Docker build (20-40 хвилин)..."
> @echo "   📊 Монітор пам'яті (у іншому терміналі):"
> @echo "      watch -n 2 'free -h; echo; docker stats --no-stream'"
> docker compose -f docker-compose.orangepi.yml build --no-cache app --progress=plain 2>&1 | tee build-$$(date +%Y%m%d-%H%M%S).log
> @echo "✅ Збірка завершена"

opi-up:
> @echo "${YELLOW}[OPI] Запуск сервісів Orange Pi...${RESET}"
> docker compose -f docker-compose.orangepi.yml up -d

opi-logs:
> @echo "${YELLOW}[OPI] Потокові логи Orange Pi...${RESET}"
> docker compose -f docker-compose.orangepi.yml logs -f

opi-shell:
> @echo "${YELLOW}[OPI] Shell у контейнері opi-executor...${RESET}"
> docker compose -f docker-compose.orangepi.yml exec opi-executor /bin/bash

opi-down:
> @echo "${YELLOW}[OPI] Зупинка сервісів Orange Pi та очищення контейнерів...${RESET}"
> docker compose -f docker-compose.orangepi.yml down

opi-health:
> @echo "🍊 Orange Pi Zero: Health check..."
> curl -s http://localhost:8000/healthz | python -m json.tool
> @echo "✅ Відповідає нормально"

# Діагностика
health-all:
> @echo "${GREEN}[HEALTH] Перевірка всіх сервісів...${RESET}"
> docker compose -f docker-compose.pc.yml ps
> docker compose -f docker-compose.orangepi.yml ps

monitor-mqtt:
> @echo "${GREEN}[MQTT] Моніторинг greenhouse/#...${RESET}"
> mosquitto_sub -h ${MQTT_HOST:-localhost} -t "greenhouse/#" -v

test-connection:
> @echo "${GREEN}[NET] Тест з'єднання ПК <-> OPI...${RESET}"
> curl -f http://localhost:8080/system_status || true
> curl -f http://localhost:8000/healthz || true

# Загальні команди
start:
> docker compose up -d

logs:
> docker compose logs -f

stop-all: pc-down opi-down
> @echo "${BOLD}[ALL] Усі сервіси ПК та Orange Pi зупинено.${RESET}"

monitor:
> docker compose exec mqtt mosquitto_sub -h localhost -t 'arm/#' -v

test-camera:
> curl http://localhost:8000/camera/snapshot -o test.jpg
> curl http://localhost:8000/camera/settings | jq

fix-camera:
> curl -X POST http://localhost:8000/camera/settings \
>         -H "Content-Type: application/json" \
>         -d '{"exposure": 200, "brightness": 150, "gain": 80}'

train:
> curl -X POST http://localhost:8000/control/start \
>         -H "Content-Type: application/json" \
>         -d '{"task": "Навчитися рухати роборукою"}'

dashboard:
> cd monitoring && python3 -m http.server 8888

# Розгортання
deploy-pc: pc-build pc-up
> @echo "${BLUE}[PC] Розгортання завершено.${RESET}"

deploy-opi: opi-build opi-up
> @echo "${YELLOW}[OPI] Розгортання завершено.${RESET}"
