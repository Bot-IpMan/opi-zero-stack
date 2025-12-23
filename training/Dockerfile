FROM python:3.10-slim

ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1

WORKDIR /training

# Встановлення системних залежностей
# Замість libgl1-mesa-glx (застаріле) - використовуємо libgl1 та інші
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Встановлення Python залежностей
COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt

# Копіювання коду
COPY . .

# Створення директорій для результатів
RUN mkdir -p models logs tensorboard

# Запуск навчання
CMD ["python", "train_ppo.py"]
