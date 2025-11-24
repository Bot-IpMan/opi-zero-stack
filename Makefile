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

%:
	@:
