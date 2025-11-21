FROM python:3.9-slim

WORKDIR /detection

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx libglib2.0-0 \
    libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p models logs

CMD ["python", "yolo_detector.py"]
