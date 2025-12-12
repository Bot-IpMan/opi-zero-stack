.DEFAULT_GOAL := help

# Colors
BOLD=\033[1m
BLUE=\033[1;34m
YELLOW=\033[1;33m
GREEN=\033[1;32m
RESET=\033[0m

.PHONY: help pc-build pc-up pc-logs pc-shell opi-build opi-up opi-logs opi-shell health-all monitor-mqtt test-connection deploy-pc deploy-opi

help:
	@echo "${BOLD}Доступні команди:${RESET}"
	@echo "  ${BLUE}make pc-build${RESET}        - Збудувати LLM сервіс для ПК"
	@echo "  ${BLUE}make pc-up${RESET}           - Запустити сервіси ПК у фоні"
	@echo "  ${BLUE}make pc-logs${RESET}         - Потокові логи ПК сервісів"
	@echo "  ${BLUE}make pc-shell${RESET}        - Відкрити shell у контейнері ПК"
	@echo "  ${YELLOW}make opi-build${RESET}       - Збудувати сервіс Orange Pi Zero"
	@echo "  ${YELLOW}make opi-up${RESET}          - Запустити сервіси Orange Pi у фоні"
	@echo "  ${YELLOW}make opi-logs${RESET}        - Потокові логи сервісів Orange Pi"
	@echo "  ${YELLOW}make opi-shell${RESET}       - Відкрити shell у контейнері Orange Pi"
	@echo "  ${GREEN}make health-all${RESET}      - Перевірка стану всіх сервісів"
	@echo "  ${GREEN}make monitor-mqtt${RESET}    - Моніторинг топіку greenhouse/# через MQTT"
	@echo "  ${GREEN}make test-connection${RESET} - Тест з'єднання між ПК та Orange Pi"
	@echo "  ${BLUE}make deploy-pc${RESET}        - Розгортання сервісів на ПК"
	@echo "  ${YELLOW}make deploy-opi${RESET}       - Розгортання сервісів на Orange Pi"

# ПК
pc-build:
	@echo "${BLUE}[PC] Збірка LLM сервісу...${RESET}"
	docker compose -f docker-compose.pc.yml build

pc-up:
	@echo "${BLUE}[PC] Запуск сервісів ПК...${RESET}"
	@CAM_DEV="$${CAMERA_DEVICE:-/dev/video0}"; \
	if [ -e "$$CAM_DEV" ]; then \
		echo "${BLUE}[PC] Камера виявлена ($$CAM_DEV). Проброшуємо пристрій...${RESET}"; \
		docker compose -f docker-compose.pc.yml -f docker-compose.pc.camera.yml up -d; \
	else \
		echo "${YELLOW}[PC] Камеру не знайдено за $$CAM_DEV, запускаємо без неї.${RESET}"; \
		docker compose -f docker-compose.pc.yml up -d; \
	fi

pc-logs:
        @echo "${BLUE}[PC] Потокові логи ПК...${RESET}"
        docker compose -f docker-compose.pc.yml logs -f

pc-shell:
        @echo "${BLUE}[PC] Shell у контейнері pc-llm...${RESET}"
        docker compose -f docker-compose.pc.yml exec pc-llm-service /bin/bash

# Orange Pi Zero
opi-build:
	@echo "${YELLOW}[OPI] Збірка сервісу Orange Pi...${RESET}"
	docker compose -f docker-compose.orangepi.yml build

opi-up:
	@echo "${YELLOW}[OPI] Запуск сервісів Orange Pi...${RESET}"
	docker compose -f docker-compose.orangepi.yml up -d

opi-logs:
	@echo "${YELLOW}[OPI] Потокові логи Orange Pi...${RESET}"
	docker compose -f docker-compose.orangepi.yml logs -f

opi-shell:
	@echo "${YELLOW}[OPI] Shell у контейнері opi-executor...${RESET}"
	docker compose -f docker-compose.orangepi.yml exec opi-executor /bin/bash

# Діагностика
health-all:
	@echo "${GREEN}[HEALTH] Перевірка всіх сервісів...${RESET}"
	docker compose -f docker-compose.pc.yml ps
	docker compose -f docker-compose.orangepi.yml ps

monitor-mqtt:
	@echo "${GREEN}[MQTT] Моніторинг greenhouse/#...${RESET}"
	mosquitto_sub -h ${MQTT_HOST:-localhost} -t "greenhouse/#" -v

test-connection:
	@echo "${GREEN}[NET] Тест з'єднання ПК <-> OPI...${RESET}"
	curl -f http://localhost:8080/system_status || true
	curl -f http://localhost:8000/healthz || true

# Розгортання
deploy-pc: pc-build pc-up
	@echo "${BLUE}[PC] Розгортання завершено.${RESET}"

deploy-opi: opi-build opi-up
	@echo "${YELLOW}[OPI] Розгортання завершено.${RESET}"
