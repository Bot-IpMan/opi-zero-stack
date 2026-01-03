FROM python:3.11-slim

# Змінні середовища
ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

# Системні залежності
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgfortran5 \
      libopenblas0-pthread \
      ca-certificates \
      libglib2.0-0 \
      libgl1 \
      libsm6 \
      libxext6 \
      libxrender-dev \
      v4l-utils \
      curl \
      gcc \
      g++ \
      python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Встановлення Python пакетів (БЕЗ --only-binary для гнучкості на ARM)
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Перевірка що все встановилось
RUN python -c "import tflite_runtime; print('TFLite OK:', tflite_runtime.__version__)" && \
    python -c "import cv2; print('OpenCV OK:', cv2.__version__)" && \
    python -c "import numpy; print('NumPy OK:', numpy.__version__)"

# Код і модель
COPY main.py model.tflite ./

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
