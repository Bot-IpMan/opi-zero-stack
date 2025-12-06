FROM python:3.11-slim

# Faster installs on ARM (piwheels) with binary-only policy to avoid source builds
ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1

# Runtime deps for OpenCV + BLAS used by NumPy (Debian 12+ package names)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 libglib2.0-0t64 libsm6 libxext6 libxrender-dev libgomp1 \
      libgfortran5 libopenblas0-pthread \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /detection
COPY requirements.txt ./

# Force wheel installs to avoid compiling OpenCV / NumPy from source
RUN pip install --only-binary=:all: -r requirements.txt

COPY . .
CMD ["python", "yolo_detector.py"]
