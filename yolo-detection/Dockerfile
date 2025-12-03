FROM python:3.9-slim

WORKDIR /detection

# Системні залежності для OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0t64 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Python залежності
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код
COPY . .

CMD ["python", "yolo_detector.py"]
