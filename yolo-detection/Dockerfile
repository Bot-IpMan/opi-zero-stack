FROM debian:bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1

# Install python3 and python3-opencv (pre-built for ARM)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-opencv \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /yolo-detection

COPY requirements.txt .

# Install other dependencies (excluding opencv)
RUN pip3 install --prefer-binary --timeout=600 --retries 5 \
    --extra-index-url https://www.piwheels.org/simple \
    -r requirements.txt

# Verify OpenCV works
RUN python3 -c "import cv2; print(f'OpenCV {cv2.__version__} OK')"

COPY . .

CMD ["python3", "yolo_detector.py"]