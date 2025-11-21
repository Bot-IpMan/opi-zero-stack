#!/usr/bin/env python3
"""
YOLO Detector на Orange Pi PC
Читає камеру → детектує об'єкти → публікує в MQTT
"""

import cv2
import json
import time
import logging
import paho.mqtt.client as mqtt
from ultralytics import YOLO
from threading import Thread
from queue import Queue

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YOLODetector:
    def __init__(self, model_name="yolov8n", mqtt_host="mqtt", mqtt_port=1883):
        self.model = YOLO(model_name + ".pt")  # nano модель
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        
        # MQTT клієнт
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        # Камера
        self.cap = cv2.VideoCapture("/dev/video0")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.frame_queue = Queue(maxsize=2)
        self.running = True
        
        logger.info("🎥 YOLO Detector ініціалізовано")
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("✅ MQTT підключено")
        else:
            logger.error(f"❌ MQTT помилка {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        logger.warning(f"⚠️ MQTT розключено {rc}")
    
    def camera_thread(self):
        """Читання кадрів з камери"""
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Залишити тільки останній кадр
                if not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                self.frame_queue.put(frame)
            time.sleep(0.01)
    
    def detect_loop(self):
        """Основний цикл детекції"""
        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.mqtt_client.loop_start()
        
        # Запуск камери
        camera = Thread(target=self.camera_thread, daemon=True)
        camera.start()
        
        logger.info("🚀 Цикл детекції запущено")
        
        try:
            while self.running:
                if self.frame_queue.empty():
                    time.sleep(0.01)
                    continue
                
                frame = self.frame_queue.get()
                start_time = time.time()
                
                # YOLO інференс
                results = self.model(frame, verbose=False, conf=0.5)
                
                # Парсинг результатів
                detections = []
                for r in results:
                    boxes = r.boxes
                    for box in boxes:
                        x1, y1, x2, y2 = box.xyxy[0].tolist()
                        conf = box.conf[0].item()
                        cls = int(box.cls[0].item())
                        cls_name = self.model.names[cls]
                        
                        # Центр bbox у нормалізованих координатах
                        cx = ((x1 + x2) / 2) / frame.shape[1]
                        cy = ((y1 + y2) / 2) / frame.shape[0]
                        
                        detections.append({
                            "class": cls_name,
                            "x": cx,
                            "y": cy,
                            "confidence": conf
                        })
                
                # MQTT публікація
                payload = {
                    "timestamp": time.time(),
                    "objects": detections,
                    "inference_time_ms": (time.time() - start_time) * 1000
                }
                
                self.mqtt_client.publish(
                    "arm/vision/objects",
                    json.dumps(payload),
                    qos=1
                )
                
                # Статистика
                print(f"📷 {len(detections)} об'єктів | " +
                      f"Inference: {payload['inference_time_ms']:.1f}ms", 
                      end='\r')
        
        except KeyboardInterrupt:
            logger.info("🛑 Зупинка...")
        finally:
            self.running = False
            self.cap.release()
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

if __name__ == "__main__":
    import os
    mqtt_host = os.getenv("MQTT_HOST", "mqtt")
    
    detector = YOLODetector(mqtt_host=mqtt_host)
    detector.detect_loop()
