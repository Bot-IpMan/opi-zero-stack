FROM python:3.11-slim-bookworm

ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      libgfortran5 libopenblas0-pthread python3-numpy ca-certificates \
      libatomic1 \
      v4l-utils curl \
      patch \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

RUN mkdir -p ./wheels
COPY wheels/ ./wheels/

RUN pip install --prefer-binary --timeout=300 --retries 5 \
    --find-links=./wheels/ \
    -r requirements.txt

COPY main.py model.tflite ./

EXPOSE 8000
CMD ["python", "-u", "main.py"]
