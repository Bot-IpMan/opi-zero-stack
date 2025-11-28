# training/Dockerfile

FROM python:3.10-slim

WORKDIR /training

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Встановлення залежностей для навчання
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Встановлення залежностей для експорту
COPY requirements-export.txt .
RUN pip install --no-cache-dir -r requirements-export.txt || true

COPY . .
RUN mkdir -p models logs tensorboard

CMD ["python", "train_ppo.py"]
