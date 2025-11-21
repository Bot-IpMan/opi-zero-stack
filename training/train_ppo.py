#!/usr/bin/env python3
import os
import torch
import argparse
from datetime import datetime
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import CheckpointCallback
from stable_baselines3.common.vec_env import VecNormalize
from environments.robot_arm_env import RobotArmEnv

def train(args):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_name = f"ppo_robotarm_yolo_{timestamp}"
    
    models_dir = f"models/{run_name}"
    tensorboard_dir = f"tensorboard/{run_name}"
    os.makedirs(models_dir, exist_ok=True)
    
    print(f"🚀 YOLO-aware RL training: {run_name}")
    
    # Векторизоване середовище
    env = make_vec_env(RobotArmEnv, n_envs=args.n_envs)
    env = VecNormalize(env, norm_obs=True, norm_reward=True)
    
    checkpoint_callback = CheckpointCallback(
        save_freq=args.save_freq,
        save_path=models_dir,
        name_prefix='rl_model',
        save_vecnormalize=True
    )
    
    # PPO з меншою мережею (легше для TFLite)
    model = PPO(
        "MlpPolicy",
        env,
        learning_rate=args.lr,
        n_steps=args.n_steps,
        batch_size=args.batch_size,
        n_epochs=args.n_epochs,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        verbose=1,
        tensorboard_log=tensorboard_dir,
        policy_kwargs={
            "net_arch": [128, 128],  # Меньше = легче для TFLite
            "activation_fn": torch.nn.ReLU
        }
    )
    
    print(f"🏋️ Навчання на {args.total_timesteps:,} timesteps...")
    model.learn(
        total_timesteps=args.total_timesteps,
        callback=checkpoint_callback,
        progress_bar=True
    )
    
    # Збереження
    final_path = f"{models_dir}/final_model"
    model.save(final_path)
    env.save(f"{models_dir}/vec_normalize.pkl")
    
    print(f"✅ Модель збережено: {final_path}")
    return final_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--total-timesteps", type=int, default=500_000)
    parser.add_argument("--n-envs", type=int, default=4)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--n-steps", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--n-epochs", type=int, default=10)
    parser.add_argument("--save-freq", type=int, default=25000)
    
    args = parser.parse_args()
    train(args)
