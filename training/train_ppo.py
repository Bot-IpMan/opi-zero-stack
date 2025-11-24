"""Train PPO policy for the PyBullet arm and save artifacts described in README."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv, VecNormalize

from environments.robot_arm_env import RobotArmEnv


def build_env(n_envs: int, norm: bool = True):
    vec_cls = DummyVecEnv if n_envs == 1 else SubprocVecEnv
    env = make_vec_env(RobotArmEnv, n_envs=n_envs, vec_env_cls=vec_cls)
    if norm:
        env = VecNormalize(env, norm_obs=True, norm_reward=True, clip_obs=5.0)
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PPO policy for the robot arm")
    parser.add_argument("--total-timesteps", type=int, default=500_000, help="Number of PPO timesteps to run")
    parser.add_argument("--n-envs", type=int, default=4, help="Parallel Gym environments to accelerate experience collection")
    parser.add_argument("--batch-size", type=int, default=128, help="PPO batch size")
    parser.add_argument("--learning-rate", type=float, default=3e-4, help="Optimizer learning rate")
    parser.add_argument(
        "--policy-hidden-dims",
        type=int,
        nargs="+",
        default=[128, 128],
        help="Hidden layer sizes for both policy and value networks (e.g. 128 128)",
    )
    parser.add_argument("--model-dir", type=Path, default=Path("models"), help="Where to store trained weights")
    parser.add_argument(
        "--tensorboard-dir",
        type=Path,
        default=Path("models") / "tb",
        help="TensorBoard log directory (mounted to tensorboard service)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.model_dir.mkdir(parents=True, exist_ok=True)
    args.tensorboard_dir.mkdir(parents=True, exist_ok=True)

    policy_net: Sequence[int] = list(args.policy_hidden_dims)
    n_steps = max(64, (2048 // args.n_envs) * args.n_envs)

    print("🚀 Starting PPO training...")
    print(f"Parallel envs: {args.n_envs} | Total timesteps: {args.total_timesteps}")
    print(f"Policy hidden dims: {policy_net} | Batch size: {args.batch_size}")

    env = build_env(args.n_envs)
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        batch_size=args.batch_size,
        n_steps=n_steps,
        learning_rate=args.learning_rate,
        tensorboard_log=str(args.tensorboard_dir),
        policy_kwargs={"net_arch": [dict(pi=policy_net, vf=policy_net)]},
    )
    model.learn(total_timesteps=args.total_timesteps)

    model_path = args.model_dir / "ppo_model.zip"
    model.save(model_path)
    env.save(args.model_dir / "vec_normalize.pkl")
    env.close()

    print(f"Saved PPO model to {model_path}")
    print(f"Saved VecNormalize statistics to {args.model_dir / 'vec_normalize.pkl'}")


if __name__ == "__main__":
    main()
