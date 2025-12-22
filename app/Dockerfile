FROM python:3.11-slim-bookworm

# 🔴 КРИТИЧНО ДЛЯ ORANGE PI ZERO:
# - OPENBLAS мultithreading OFF (тільки 1 ядро)
# - NUMPY на ARM вже слабкий, без OMP -> краще
# - TFLite pre-built, не компілюється

ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    ARMV6=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgfortran5 libopenblas0-pthread ca-certificates \
      v4l-utils curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app
COPY requirements-orangepi-zero.txt requirements.txt .

# 🟢 КЛЮЧ: --prefer-binary + piwheels (ТІЛЬКИ wheels, НІ компіляції!)
# timeout=300 (5 хвилин, не 15 сек) - Orange Pi Zero дуже повільна
RUN pip install --prefer-binary \
      -r requirements.txt \
      --timeout=300 \
      --retries 5

COPY main.py model.tflite ./

EXPOSE 8000
CMD ["python", "-u", "main.py"]
