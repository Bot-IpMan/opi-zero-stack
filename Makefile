.PHONY: train tensorboard export clean stack up down

train:
	TRAIN_ARGS="$(filter-out $@ --,$(MAKECMDGOALS))" docker compose -f docker-compose.train.yml up --build training

tensorboard:
	docker compose -f docker-compose.train.yml up tensorboard

export:
	docker compose -f docker-compose.train.yml run --rm training python export_models.py

clean:
	docker compose -f docker-compose.train.yml down --volumes --remove-orphans

stack:
	docker compose up --build

up: stack
	docker compose logs -f

down:
	docker compose down

healthz:
	docker compose exec app curl -sf http://localhost:8000/healthz

test-predict:
	docker compose exec app curl -sf -X POST http://localhost:8000/predict \
	  -H 'Content-Type: application/json' \
	  -d '{"x":[0,0,0,0,0,0]}'

monitor:
	docker compose exec mqttc mosquitto_sub -h mqtt -t 'arm/#' -v

logs-app:
	docker compose logs -f app

logs-mqtt:
	docker compose logs -f mqtt

logs-yolo:
	docker compose logs -f yolo-detector

shell-app:
	docker compose exec app /bin/sh

shell-yolo:
	docker compose exec yolo-detector /bin/sh

build-yolo:
	docker compose build yolo-detector

up-yolo:
	docker compose up -d yolo-detector

%:
	@:
