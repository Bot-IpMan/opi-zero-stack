.PHONY: train stack up down

train:
	docker compose -f docker-compose.train.yml up --build

stack:
	docker compose up --build

up: stack
	docker compose logs -f

down:
	docker compose down
