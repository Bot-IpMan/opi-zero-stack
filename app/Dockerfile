FROM python:3.11-slim-bookworm

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1

# Системні lib + numpy з apt (НЕ pip!)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgfortran5 libopenblas0-pthread \
      python3-numpy \
      ca-certificates curl v4l-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-orangepi-zero.txt requirements.txt .
COPY wheels/ ./wheels/

# Встановити все з локальних wheels + piwheels
RUN pip install --prefer-binary \
      --find-links=./wheels/ \
      -r requirements.txt \
      --timeout=300

# Заповнити бінарні залежності
RUN pip install --no-index --find-links=./wheels/ \
      tflite_runtime 2>/dev/null || \
    pip install --prefer-binary \
      https://github.com/PINTO0309/TensorflowLite-bin/releases/download/v2.14.0.post1/tflite_runtime-2.14.0.post1-cp311-none-linux_armv7l.whl

COPY main.py model.tflite ./

EXPOSE 8000
CMD ["python", "-u", "main.py"]
