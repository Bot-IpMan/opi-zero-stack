#!/usr/bin/env python3
import os
import numpy as np
import tensorflow as tf
from stable_baselines3 import PPO

def convert_to_tflite(model_path, output_path, quantize=True):
    """Конвертація PPO → TFLite з INT8 квантизацією"""
    
    print(f"🔄 Завантаження моделі...")
    model = PPO.load(model_path)
    policy = model.policy
    
    # TensorFlow wrapper
    class PolicyWrapper(tf.Module):
        def __init__(self, sb3_policy):
            super().__init__()
            self.policy = sb3_policy
        
        @tf.function(input_signature=[
            tf.TensorSpec(shape=[1, 9], dtype=tf.float32)
        ])
        def __call__(self, obs):
            import torch
            with torch.no_grad():
                obs_tensor = torch.FloatTensor(obs.numpy())
                action, _ = self.policy.predict(obs_tensor, deterministic=True)
            return tf.constant(action, dtype=tf.float32)
    
    tf_model = PolicyWrapper(policy)
    concrete_func = tf_model.__call__.get_concrete_function()
    
    # Конвертація
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])
    
    if quantize:
        print("🔧 INT8 квантизація...")
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        
        def representative_dataset():
            for _ in range(100):
                yield [np.random.randn(1, 9).astype(np.float32)]
        
        converter.representative_dataset = representative_dataset
    
    tflite_model = converter.convert()
    
    # Збереження
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    size_kb = len(tflite_model) / 1024
    print(f"✅ TFLite модель: {output_path} ({size_kb:.1f} KB)")
    
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", default="model.tflite")
    args = parser.parse_args()
    
    convert_to_tflite(args.model, args.output)
