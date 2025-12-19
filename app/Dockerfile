# Base image kept on Docker Hub to avoid intermittent TLS handshake issues with ECR.
ARG PYTHON_BASE=python:3.11-slim-bookworm
FROM ${PYTHON_BASE}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Встановити OpenCV через apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-opencv \
    libopencv-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libatlas-base-dev \
    libjpeg-dev \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --prefer-binary numpy==1.26.4
RUN pip install --prefer-binary -r requirements.txt

COPY . .
RUN mkdir -p /app/logs /app/models

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
