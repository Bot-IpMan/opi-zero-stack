FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=2 \
    OPENBLAS_NUM_THREADS=2

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /service
COPY requirements.txt ./
# Install CPU-optimised wheels to minimise download size and avoid exhausting
# limited build-space on hosts with small Docker storage.
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir --prefer-binary --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

COPY . .
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--loop", "asyncio"]
