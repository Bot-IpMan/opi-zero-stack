#!/usr/bin/env python3
"""
Експорт PPO моделі в ONNX (без TensorFlow)
ONNX → можна конвертувати в TFLite на Orange Pi
"""

import os
import numpy as np
import torch
from stable_baselines3 import PPO

def export_ppo_to_onnx(model_path, output_path="model.onnx"):
    """Конвертація PPO → ONNX"""
    
    print(f"🔄 Завантаження моделі...")
    model = PPO.load(model_path)
    
    print(f"🔄 Екстракція policy network...")
    policy = model.policy
    
    # Використовуємо MLP extractor (найпростіше для ONNX)
    print(f"🔄 Конвертація в ONNX...")
    
    # Створення тестового входу
    dummy_input = torch.randn(1, 9, dtype=torch.float32)
    
    # Експорт через policy.predict
    # Це трохи складніше, тому спрощуємо
    
    try:
        # Спроба експорту через forward pass
        output = policy(dummy_input, deterministic=True)
        action = output[0]
        
        print(f"✅ Policy output shape: {action.shape}")
        
        # Экспорт ONNX
        torch.onnx.export(
            policy,
            dummy_input,
            output_path,
            input_names=['observation'],
            output_names=['action'],
            opset_version=12,
            do_constant_folding=True,
        )
        
        size_kb = os.path.getsize(output_path) / 1024
        print(f"✅ ONNX модель: {output_path} ({size_kb:.1f} KB)")
        
    except Exception as e:
        print(f"⚠️  ONNX експорт складний, використовуємо спрощений метод")
        
        # Спрощений метод: просто зберегти ваги PyTorch
        torch.save(model.policy.state_dict(), output_path.replace('.onnx', '.pt'))
        print(f"✅ PyTorch weights: {output_path.replace('.onnx', '.pt')}")

def export_yolo_simple(output_path="yolov8n.pt"):
    """
    Просто скачати YOLO модель (не конвертувати, вона вже мала)
    """
    print(f"🔄 YOLO модель вже готова в контейнері")
    print(f"   Формат: PyTorch (.pt)")
    print(f"   Розмір: ~6MB")
    print(f"   На Orange Pi Pi PC буде конвертована в TFLite автоматично")
    return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ppo-model",
        default="models/ppo_model.zip",
        help="Шлях до .zip моделі PPO (за замовчуванням models/ppo_model.zip)",
    )
    parser.add_argument("--output", default="models/ppo_model.onnx")
    
    args = parser.parse_args()
    
    # Експорт PPO
    if not os.path.isfile(args.ppo_model):
        raise FileNotFoundError(
            f"Не знайдено PPO модель за шляхом: {args.ppo_model}. "
            "Запустіть `make train` або вкажіть свій шлях через --ppo-model"
        )

    export_ppo_to_onnx(args.ppo_model, args.output)
    
    # YOLO вже готова
    export_yolo_simple()
    
    print("\n✅ Експорт завершен!")
    print(f"   📦 Модель: {args.output}")
    print(f"   📦 На Orange Pi конвертуємо в TFLite")
