#!/usr/bin/env python3
"""
Експорт PPO модели в ONNX → TFLite
"""

import torch
import numpy as np
from stable_baselines3 import PPO
import onnx
import onnxruntime

def export_ppo_to_onnx(model_path, output_path):
    """Конвертація PPO → ONNX"""
    
    print(f"🔄 Завантаження моделі...")
    model = PPO.load(model_path)
    policy = model.policy
    
    # Експорт в ONNX
    dummy_input = torch.randn(1, 9)
    torch.onnx.export(
        policy.mlp_extractor.policy_net,
        dummy_input,
        output_path,
        input_names=['observation'],
        output_names=['action'],
        opset_version=12
    )
    
    print(f"✅ ONNX модель: {output_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--ppo-model", required=True)
    parser.add_argument("--output", default="model.onnx")
    
    args = parser.parse_args()
    export_ppo_to_onnx(args.ppo_model, args.output)
