# app/Dockerfile
FROM python:3.11-slim

# 1) Готові ARMv7-вheels з piwheels + fallback на PyPI
ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # приглушити багатопоточність BLAS на слабкому CPU
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

# 2) Рантайм-ліби для NumPy + утиліти для камери та healthcheck
#    (libgfortran5, libopenblas0-pthread — це прямо рекомендація під NumPy на ARM; v4l-utils дає v4l2-ctl)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgfortran5 libopenblas0-pthread ca-certificates \
      libglib2.0-0 libgl1 python3-opencv \
      v4l-utils curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# 3) Забороняємо збірку з сирців — тільки wheels (на ARM це критично)
RUN pip install --only-binary=:all: -r requirements.txt

# 4) Код і мінімальна FP32-модель TFLite (TFL3)
COPY main.py model.tflite ./

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
