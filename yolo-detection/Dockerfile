FROM python:3.9-slim

WORKDIR /detection

# Встановити компіляторів та необхідних залежностей ДО pip install
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    libgomp1 \
    libglib2.0-0t64 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Оновити pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# NumPy окремо (потреба часу на компіляцію armv7l)
RUN pip install --no-cache-dir numpy==1.24.3

# OpenCV та інші залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY . .

CMD ["python", "yolo_detector.py"]
