"""PPO training entrypoint for the robot arm environment."""
from __future__ import annotations

from pathlib import Path

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

from environments.robot_arm_env import RobotArmEnv


def build_env():
    return DummyVecEnv([lambda: RobotArmEnv()])


def main():
    env = build_env()
    model = PPO("CnnPolicy", env, verbose=1)
    model.learn(total_timesteps=1_000)

    models_dir = Path("models")
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "ppo_model.zip"
    model.save(model_path)
    print(f"Saved PPO model to {model_path}")


if __name__ == "__main__":
    main()
