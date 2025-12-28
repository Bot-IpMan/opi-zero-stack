.PHONY: train pc-export pc-deploy pc-build \
        opi-prepare opi-fix-requirements opi-fix-opencv opi-build opi-up opi-logs opi-health opi-down

# ========== PC (НАВЧАННЯ) ==========

train:
	@echo "🖥️ ПК: Запуск PPO навчання..."
	docker compose -f docker-compose.train.yml up training

pc-export:
        @echo "🖥️ ПК: Експорт моделі в TFLite..."
        docker compose -f docker-compose.train.yml run --rm training python export_models.py \
                --ppo-model training/models/final_model.zip \
                --ppo-output training/models/ppo_model.tflite
        @echo "✅ Модель експортована"

pc-deploy:
        @echo "🖥️ ПК: Копіювання на Orange Pi Zero..."
        @read -p "Введіть IP Orange Pi Zero (192.168.1.101): " IP; \
        scp training/models/ppo_model.tflite orangepi@$$IP:~/opi-zero-stack/app/model.tflite
        @echo "✅ Готово"

pc-build:
        @echo "🖥️ ПК: Збірка Docker-образів для локального середовища..."
        docker compose -f docker-compose.pc.yml build
        @echo "✅ Збірка завершена"

# ========== ORANGE PI ZERO ==========

opi-prepare:
	@echo "🍊 Orange Pi Zero: Підготовка (swap, очистка)..."
	@sudo swapoff -a 2>/dev/null || true
	@sudo fallocate -l 2G /swapfile 2>/dev/null || true
	@sudo chmod 600 /swapfile 2>/dev/null || true
	@sudo mkswap /swapfile 2>/dev/null || true
	@sudo swapon /swapfile 2>/dev/null || true
	@echo "✅ Swap 2GB включено"
	@if command -v free >/dev/null 2>&1; then \
		free -h 2>/dev/null | grep -i swap || true; \
	else \
		echo "ℹ️ free command недоступна"; \
	fi

opi-fix-requirements:
	@echo "🍊 Orange Pi Zero: Виправлення requirements.txt..."
	@if grep -q "opencv-python-headless" app/requirements.txt; then \
		sed -i 's/opencv-python-headless==[^ ]\+/opencv-python-headless==4.8.0.76/g' app/requirements.txt; \
	else \
		echo "opencv-python-headless==4.8.0.76" >> app/requirements.txt; \
	fi
	@grep opencv app/requirements.txt || true
	@echo "✅ OpenCV версія оновлена або додана"

opi-fix-opencv:
	@echo "🍊 Orange Pi Zero: Встановлення build-essential для OpenCV..."
	@docker compose -f docker-compose.yml exec -T app apt-get update && \
	  apt-get install -y build-essential cmake || true
	@echo "✅ Build tools встановлені"

opi-build: opi-prepare opi-fix-requirements
	@echo "🍊 Orange Pi Zero: Docker build (20-40 хвилин)..."
	@echo "   Монітор пам'яті (у іншому терміналі): watch -n 2 'free -h'"
	docker compose -f docker-compose.yml build --no-cache app --progress=plain 2>&1 | \
		tee build-$$(date +%Y%m%d-%H%M%S).log
	@echo "✅ Збірка завершена"

opi-up:
	@echo "🍊 Orange Pi Zero: Запуск сервісу..."
	docker compose -f docker-compose.yml up -d mqtt app
	@sleep 2
	docker compose -f docker-compose.yml logs app

opi-logs:
	docker compose -f docker-compose.yml logs -f app

opi-health:
	@echo "🍊 Orange Pi Zero: Health check..."
	curl -s http://localhost:8000/healthz | python -m json.tool

opi-down:
	@echo "🍊 Orange Pi Zero: Зупинення..."
	docker compose -f docker-compose.yml down

# ========== ДОПОМІЖНІ ==========

.PHONY: help
help:
        @echo "=== RELEASE 0.0.2 COMMANDS ==="
        @echo ""
        @echo "PC (навчання):"
        @echo "  make train        - Запуск PPO навчання"
        @echo "  make pc-export    - Експорт моделі в TFLite"
        @echo "  make pc-deploy    - Копіювання на Orange Pi Zero"
        @echo "  make pc-build     - Збірка Docker образів для ПК"
        @echo ""
        @echo "Orange Pi Zero (запуск):"
        @echo "  make opi-prepare        - Включити swap"
        @echo "  make opi-fix-requirements - Виправити requirements"
	@echo "  make opi-build          - Повна збірка (20-40 хв)"
	@echo "  make opi-up             - Запустити сервіс"
	@echo "  make opi-logs           - Показати логи"
	@echo "  make opi-health         - Health check"
	@echo "  make opi-down           - Зупинити все"
