#!/usr/bin/env python3
"""
YOLO Detector - Спрощена версія (емуляція детекцій)
"""

import cv2
import json
import time
import logging
import os
import numpy as np
import paho.mqtt.client as mqtt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleDetector:
    def __init__(self, mqtt_host="mqtt", mqtt_port=1883):
        """Емуляція YOLO детекцій"""
        
        # MQTT
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(mqtt_host, mqtt_port, 60)
        
        # Камера
        self.cap = cv2.VideoCapture("/dev/video0")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.running = True
        
        logger.info("🎥 Simple Detector ініціалізовано")
    
    def detect_loop(self):
        """Основний цикл (емуляція детекцій)"""
        self.mqtt_client.loop_start()
        
        logger.info("🚀 Детекція запущена (емуляція)")
        
        try:
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning("⚠️ Не вдалося прочитати кадр")
                    time.sleep(0.1)
                    continue
                
                start_time = time.time()
                
                # ЕМУЛЯЦІЯ детекції (випадкові координати)
                detections = [
                    {
                        "class": "object",
                        "x": np.random.uniform(0.3, 0.7),
                        "y": np.random.uniform(0.3, 0.7),
                        "confidence": np.random.uniform(0.7, 0.95)
                    }
                ]
                
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
                
                print(f"📷 {len(detections)} об'єктів | " +
                      f"FPS: {1.0/(time.time()-start_time):.1f}", 
                      end='\r')
                
                time.sleep(0.033)  # ~30 FPS
        
        except KeyboardInterrupt:
            logger.info("🛑 Зупинка...")
        finally:
            self.running = False
            self.cap.release()
            self.mqtt_client.loop_stop()

if __name__ == "__main__":
    mqtt_host = os.getenv("MQTT_HOST", "mqtt")
    
    detector = SimpleDetector(mqtt_host=mqtt_host)
    detector.detect_loop()
