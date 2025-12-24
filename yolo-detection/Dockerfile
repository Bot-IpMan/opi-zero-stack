FROM python:3.10-slim-bookworm

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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /yolo-detection

COPY requirements.txt .

RUN pip install --only-binary=:all: --timeout=300 --retries 5 -r requirements.txt

RUN python3 -c "import cv2; print(f'OpenCV {cv2.__version__} OK')"

COPY . .

CMD ["python", "yolo_detector.py"]
