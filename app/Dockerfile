FROM python:3.11-slim-bookworm

# Base pip/CPU configuration: route installs through piwheels, disable compilation
# from source and keep deterministic, low-noise Python runtime behaviour.
ENV PIP_INDEX_URL=https://www.piwheels.org/simple \
    PIP_EXTRA_INDEX_URL=https://pypi.org/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    PIP_ONLY_BINARY=:all:

# Install only the runtime system libraries needed by numpy/tflite/opencv wheels
# so pip can avoid building native extensions.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgfortran5 \
    libopenblas0-pthread \
    libblas3 \
    liblapack3 \
    v4l-utils \
    ca-certificates \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Work from the application directory inside the container.
WORKDIR /app

# Copy Python dependencies definition.
COPY requirements.txt .

# Install wheels only; if any dependency lacks a wheel on piwheels/PyPI the
# build will fail fast instead of compiling from source.
RUN pip install --only-binary=:all: --default-timeout=300 --retries 5 -r requirements.txt

# Copy application code and bundled model.
COPY main.py model.tflite ./

# Expose the service port used by the FastAPI/uvicorn entrypoint.
EXPOSE 8000

# Run the application with unbuffered output for easier logging.
CMD ["python", "-u", "main.py"]
