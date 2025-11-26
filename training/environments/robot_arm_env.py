import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import gymnasium as gym
import numpy as np
import pybullet as p
import pybullet_data


@dataclass
class ArmConfig:
    max_steps: int = 200
    action_scale: float = 0.05
    target_radius: float = 0.02
    workspace_bounds: Tuple[float, float] = (-0.35, 0.35)
    joint_limit: float = math.pi / 2


class RobotArmEnv(gym.Env):
    """PyBullet-based 6-DOF arm environment that matches README expectations.

    Observation: 9 floats -> [6 joint angles, 3 target coordinates]
    Action: 6 floats -> joint angle deltas (radians)
    Reward: -distance_to_target with small action penalty; success bonus on reach
    """

    metadata = {"render_modes": []}

    def __init__(self, render_mode: Optional[str] = None, config: Optional[ArmConfig] = None):
        super().__init__()
        self.render_mode = render_mode
        self.config = config or ArmConfig()

        self.observation_space = gym.spaces.Box(
            low=np.array([-self.config.joint_limit] * 6 + [self.config.workspace_bounds[0]] * 3, dtype=np.float32),
            high=np.array([self.config.joint_limit] * 6 + [self.config.workspace_bounds[1]] * 3, dtype=np.float32),
            dtype=np.float32,
        )
        self.action_space = gym.spaces.Box(
            low=-self.config.action_scale,
            high=self.config.action_scale,
            shape=(6,),
            dtype=np.float32,
        )

        self.physics_client: Optional[int] = None
        self.robot_id: Optional[int] = None
        self.joint_indices: list[int] = []
        self.step_count = 0
        self.target_pos = np.zeros(3, dtype=np.float32)

        self.reset()

    # Gym API ---------------------------------------------------------------
    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None):
        super().reset(seed=seed)
        self.step_count = 0

        self._reset_world()

        # Random target position in reachable workspace
        rng = self.np_random
        bound = self.config.workspace_bounds[1]
        self.target_pos = rng.uniform(low=-bound, high=bound, size=3).astype(np.float32)
        self.target_pos[2] = abs(self.target_pos[2]) + 0.05  # keep Z above the base

        # Reset joint states
        for j in self.joint_indices:
            p.resetJointState(
                self.robot_id,
                j,
                0.0,
                physicsClientId=self.physics_client,
            )
            p.setJointMotorControl2(
                self.robot_id,
                j,
                controlMode=p.POSITION_CONTROL,
                targetPosition=0.0,
                force=2.5,
                physicsClientId=self.physics_client,
            )
        p.stepSimulation(physicsClientId=self.physics_client)

        obs = self._get_obs()
        info = {"target": self.target_pos.tolist()}
        return obs, info

    def step(self, action):
        self.step_count += 1

        action = np.clip(action, self.action_space.low, self.action_space.high)
        current_angles = np.array(
            [p.getJointState(self.robot_id, j, physicsClientId=self.physics_client)[0] for j in self.joint_indices],
            dtype=np.float32,
        )
        desired_angles = np.clip(current_angles + action, -self.config.joint_limit, self.config.joint_limit)

        for idx, joint in enumerate(self.joint_indices):
            p.setJointMotorControl2(
                self.robot_id,
                joint,
                controlMode=p.POSITION_CONTROL,
                targetPosition=float(desired_angles[idx]),
                force=3.0,
                physicsClientId=self.physics_client,
            )

        for _ in range(8):
            p.stepSimulation(physicsClientId=self.physics_client)

        obs = self._get_obs()
        ee_pos = self._end_effector_position()
        dist = float(np.linalg.norm(ee_pos - self.target_pos))

        reward = -dist - 0.01 * float(np.linalg.norm(action))
        terminated = dist < self.config.target_radius
        if terminated:
            reward += 1.0

        truncated = self.step_count >= self.config.max_steps
        info = {"distance": dist, "target": self.target_pos.tolist(), "ee": ee_pos.tolist()}
        return obs, reward, terminated, truncated, info

    def render(self):  # pragma: no cover - GUI not used in tests
        return None

    def close(self):
        if self.physics_client is not None:
            p.disconnect(self.physics_client)
            self.physics_client = None

    # Helpers ---------------------------------------------------------------
    def _connect_sim(self):
        if self.physics_client is None:
            mode = p.GUI if self.render_mode == "human" else p.DIRECT
            self.physics_client = p.connect(mode)
            p.setAdditionalSearchPath(pybullet_data.getDataPath(), physicsClientId=self.physics_client)

    def _reset_world(self):
        self._connect_sim()

        p.resetSimulation(physicsClientId=self.physics_client)
        p.setTimeStep(1.0 / 120.0, physicsClientId=self.physics_client)
        p.setGravity(0, 0, -9.8, physicsClientId=self.physics_client)
        p.loadURDF("plane.urdf", physicsClientId=self.physics_client)

        urdf_path = str(Path(__file__).resolve().parent.parent / "robot_arm.urdf")
        self.robot_id = p.loadURDF(
            urdf_path,
            basePosition=[0, 0, 0],
            useFixedBase=True,
            physicsClientId=self.physics_client,
        )

        self.joint_indices = [
            j
            for j in range(p.getNumJoints(self.robot_id, physicsClientId=self.physics_client))
            if p.getJointInfo(self.robot_id, j, physicsClientId=self.physics_client)[2] == p.JOINT_REVOLUTE
        ]

        if len(self.joint_indices) != 6:
            raise RuntimeError(f"Expected 6 revolute joints, found {len(self.joint_indices)} in URDF")

    def _get_obs(self) -> np.ndarray:
        joint_angles = [
            p.getJointState(self.robot_id, j, physicsClientId=self.physics_client)[0]
            for j in self.joint_indices
        ]
        obs = np.concatenate([np.asarray(joint_angles, dtype=np.float32), self.target_pos])
        return np.clip(obs, self.observation_space.low, self.observation_space.high)

    def _end_effector_position(self) -> np.ndarray:
        ee_state = p.getLinkState(
            self.robot_id,
            self.joint_indices[-1],
            computeForwardKinematics=True,
            physicsClientId=self.physics_client,
        )
        pos = np.array(ee_state[0], dtype=np.float32)
        return pos
