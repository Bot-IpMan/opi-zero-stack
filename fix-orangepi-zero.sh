#!/usr/bin/env bash
set -euo pipefail

TARGET_DIR="$HOME/opi-zero-stack"

if [[ "$(pwd)" != "$TARGET_DIR" ]]; then
  echo "❌ Будь ласка, запустіть скрипт з $TARGET_DIR"
  exit 1
fi

backup_file() {
  local src="$1"
  local backup="$2"

  if [[ ! -f "$src" ]]; then
    echo "❌ Не знайдено файл: $src"
    exit 1
  fi

  cp -a "$src" "$backup"
}

backup_file app/Dockerfile app/Dockerfile.backup
backup_file app/requirements.txt app/requirements.txt.backup
backup_file app/main.py app/main.py.backup
backup_file docker-compose.yml docker-compose.yml.backup

cat <<'DOCKERFILE' > app/Dockerfile
FROM python:3.11-slim-bookworm

ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgfortran5 libopenblas0-pthread python3-numpy ca-certificates \
      v4l-utils curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Copy local wheels if present.
RUN --mount=type=bind,source=wheels,target=/tmp/wheels,ro,required=false \
    cp -r /tmp/wheels ./wheels 2>/dev/null || true

RUN pip install --prefer-binary --timeout=300 --retries 5 \
    --find-links=./wheels/ \
    -r requirements.txt

COPY main.py model.tflite ./

EXPOSE 8000
CMD ["python", "-u", "main.py"]
DOCKERFILE

cat <<'REQUIREMENTS' > app/requirements.txt
fastapi==0.104.1
pydantic==2.4.2
paho-mqtt==1.6.1
pyserial==3.5
httpx==0.27.2
python-multipart==0.0.6
pillow==10.4.0
opencv-python-headless==4.8.0.76
python-json-logger==2.0.7
waitress==2.1.2
REQUIREMENTS

PROMPT3_BLOCK_MARKER="PROMPT3_BLOCK_RELEASE_0_0_2"
if ! rg -q "$PROMPT3_BLOCK_MARKER" app/main.py; then
  cat <<'PY' >> app/main.py

# === PROMPT3_BLOCK_RELEASE_0_0_2 ===
# TODO: вставте новий блок коду з Prompt 3 тут.
# === PROMPT3_BLOCK_RELEASE_0_0_2 ===
PY
fi

cat <<'COMPOSE' > docker-compose.yml
# TODO: замініть вміст docker-compose.yml на новий з Prompt 4.
COMPOSE

mkdir -p app/wheels

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  docker compose -f docker-compose.yml config >/dev/null
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose -f docker-compose.yml config >/dev/null
else
  echo "⚠️ Не знайдено docker compose для перевірки YAML."
fi

cat <<'CHECKLIST'
✅ Готово! Зміни для release/0.0.2 застосовані.

Наступні дії:
1) Переконайтеся, що вставили новий блок у app/main.py (Prompt 3).
2) Перевірте, що docker-compose.yml відповідає Prompt 4.
3) Зберіть образ: docker compose build app
4) Запустіть сервіси: docker compose up -d
5) Перевірте логи: docker compose logs -f app
CHECKLIST
