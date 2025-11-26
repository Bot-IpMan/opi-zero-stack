FROM python:3.10-slim

WORKDIR /workspace/training
COPY requirements.txt ./

# Use CPU-only PyTorch wheels to avoid hardware-specific instructions that can
# crash on constrained devices (e.g., "Illegal instruction").
ARG TORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
ARG TORCH_VERSION=2.3.1
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --index-url ${TORCH_INDEX_URL} \
        torch==${TORCH_VERSION} torchvision==0.18.1 torchaudio==${TORCH_VERSION} \
    && pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "train_ppo.py"]
