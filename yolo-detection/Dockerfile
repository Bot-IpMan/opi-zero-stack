FROM python:3.9-slim

WORKDIR /detection

# Опції pip: дефолт — брати колеса з piwheels з fallback на PyPI та використовувати кеш (для швидших повторних збірок)
ARG PIP_NO_CACHE_DIR=0
ARG PIP_INDEX_URL=https://www.piwheels.org/simple
ARG PIP_EXTRA_INDEX_URL=https://pypi.org/simple
ENV PIP_NO_CACHE_DIR=${PIP_NO_CACHE_DIR} \
    PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_EXTRA_INDEX_URL=${PIP_EXTRA_INDEX_URL}

# Встановити компіляторів та необхідних залежностей ДО pip install
# libglib2.0-0 перейменовано в libglib2.0-0t64 у Debian Trixie; ставимо новий
# пакет, щоб уникнути помилки "no installation candidate" під час збірки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gfortran \
    libopenblas-dev \
    liblapack-dev \
    pkg-config \
    libgomp1 \
    libglib2.0-0t64 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Оновити pip, setuptools, wheel
RUN pip install --upgrade pip setuptools wheel

# NumPy окремо (потреба часу на компіляцію armv7l)
ARG TARGETPLATFORM
RUN if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        pip install numpy==1.24.3; \
    else \
        PIP_INDEX_URL=https://pypi.org/simple PIP_EXTRA_INDEX_URL= pip install numpy==1.24.3; \
    fi

# OpenCV та інші залежності
COPY requirements.txt .
# Використовуємо попередньо зібрані ARM-пакети з piwheels лише для armv7l,
# щоб уникнути важкої збірки opencv-python-headless та numpy на слабких платформах
RUN if [ "$TARGETPLATFORM" = "linux/arm/v7" ]; then \
        pip install -r requirements.txt; \
    else \
        PIP_INDEX_URL=https://pypi.org/simple PIP_EXTRA_INDEX_URL= pip install -r requirements.txt; \
    fi

# Код
COPY . .

CMD ["python", "yolo_detector.py"]
