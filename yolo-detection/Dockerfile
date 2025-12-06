FROM python:3.9-slim

WORKDIR /detection

# Мінімальний набір системних залежностей для armv7l (Debian Trixie)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libglib2.0-0t64 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libopenblas-dev \
    liblapack-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Оновити pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# Python залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY . .

CMD ["python", "yolo_detector.py"]
