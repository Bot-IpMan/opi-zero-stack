FROM python:3.10-slim

WORKDIR /workspace/training
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "train_ppo.py"]
