FROM python:3.11-slim-bookworm

ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender-dev \
      libgomp1 \
      libgfortran5 libopenblas0-pthread libblas3 liblapack3 \
      build-essential \
      cmake \
      ca-certificates curl v4l-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# Copy local wheels if present
COPY wheels/ ./wheels/

RUN pip install --prefer-binary --timeout=300 --retries 5 --find-links=./wheels/ \
    -r requirements.txt

COPY main.py model.tflite ./

EXPOSE 8000
CMD ["python", "-u", "main.py"]
