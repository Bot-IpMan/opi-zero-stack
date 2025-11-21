"""Train PPO policy for the PyBullet arm and save artifacts described in README."""
from __future__ import annotations

import argparse
from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from environments.robot_arm_env import RobotArmEnv


def build_env(norm: bool = True):
    env = DummyVecEnv([lambda: RobotArmEnv()])
    if norm:
        env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=5.0)
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PPO policy for the robot arm")
    parser.add_argument("--timesteps", type=int, default=10_000, help="Number of PPO timesteps to run")
    parser.add_argument("--model-dir", type=Path, default=Path("models"), help="Where to store trained weights")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.model_dir.mkdir(parents=True, exist_ok=True)

    env = build_env()
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        batch_size=128,
        n_steps=1024,
        tensorboard_log=str(args.model_dir / "tb"),
    )
    model.learn(total_timesteps=args.timesteps)

    model_path = args.model_dir / "ppo_model.zip"
    model.save(model_path)
    env.save(args.model_dir / "vec_normalize.pkl")

    print(f"Saved PPO model to {model_path}")
    print(f"Saved VecNormalize statistics to {args.model_dir / 'vec_normalize.pkl'}")


if __name__ == "__main__":
    main()
