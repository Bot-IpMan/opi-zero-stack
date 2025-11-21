FROM python:3.10-slim

WORKDIR /workspace/yolo-detection
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["python", "yolo_detector.py"]
