FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple

# Мінімальні системні залежності
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
      libgfortran5 \
      libopenblas0-pthread \
      python3-opencv \
      libopencv-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Встановлення пакетів з piwheels (готові wheels для ARM)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Перевірка критичних залежностей
RUN python -c "import tflite_runtime; print('✅ TFLite OK')" && \
    python -c "import numpy; print('✅ NumPy OK')" && \
    python -c "import serial; print('✅ Serial OK')" && \
    python -c "import fastapi; print('✅ FastAPI OK')"

COPY main.py model.tflite ./

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
