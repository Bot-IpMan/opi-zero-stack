FROM python:3.9-slim

WORKDIR /detection

# Системні залежності для OpenCV та armv7l
RUN apt-get update && apt-get install -y \
    libatlas-base-dev \
    libjasper-dev \
    libtiff-dev \
    libharfbuzz0b \
    libwebp6 \
    libopenjp2-7 \
    libjasper1 \
    libopenblas-dev \
    liblapack-dev \
    liblapacke \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Python залежності (без кешу для armv7l)
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Код
COPY . .

CMD ["python", "yolo_detector.py"]
