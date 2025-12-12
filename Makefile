.PHONY: pc-build pc-up pc-logs pc-shell opi-build opi-up opi-logs opi-shell health-all monitor-mqtt test-connection deploy-pc deploy-opi

# ПК
pc-build:
@echo "\033[1;34m[PC] Build LLM service\033[0m"
docker compose -f docker-compose.pc.yml build

pc-up:
@echo "\033[1;34m[PC] Up services\033[0m"
docker compose -f docker-compose.pc.yml up -d

pc-logs:
@echo "\033[1;34m[PC] Logs\033[0m"
docker compose -f docker-compose.pc.yml logs -f

pc-shell:
@echo "\033[1;34m[PC] Shell into container\033[0m"
docker compose -f docker-compose.pc.yml exec pc-llm /bin/bash

# Orange Pi Zero
opi-build:
@echo "\033[1;33m[OPI] Build executor\033[0m"
docker compose -f docker-compose.orangepi.yml build

opi-up:
@echo "\033[1;33m[OPI] Up services\033[0m"
docker compose -f docker-compose.orangepi.yml up -d

opi-logs:
@echo "\033[1;33m[OPI] Logs\033[0m"
docker compose -f docker-compose.orangepi.yml logs -f

opi-shell:
@echo "\033[1;33m[OPI] Shell into container\033[0m"
docker compose -f docker-compose.orangepi.yml exec opi-executor /bin/bash

# Діагностика
health-all:
@echo "\033[1;32m[HEALTH] Checking all services\033[0m"
docker compose -f docker-compose.pc.yml ps
docker compose -f docker-compose.orangepi.yml ps

monitor-mqtt:
@echo "\033[1;32m[MQTT] Subscribing to greenhouse/#\033[0m"
mosquitto_sub -h ${MQTT_HOST:-localhost} -t "greenhouse/#" -v

test-connection:
@echo "\033[1;32m[NET] Testing PC <-> OPI\033[0m"
curl -f http://localhost:8080/system_status || true
curl -f http://localhost:8000/healthz || true

# Розгортання
deploy-pc: pc-build pc-up
@echo "\033[1;34m[PC] Deployed\033[0m"

deploy-opi: opi-build opi-up
@echo "\033[1;33m[OPI] Deployed\033[0m"
