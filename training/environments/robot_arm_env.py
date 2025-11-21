import gymnasium as gym
import numpy as np
import pybullet as p
import pybullet_data
from gymnasium import spaces

class RobotArmEnv(gym.Env):
    """
    6-DOF роборука з детекцією YOLO
    Observation: [joint_positions(6), detected_objects(3)]
      - detected_objects: [x, y, confidence] від YOLO
    Action: [joint_angles(6)]
    """
    metadata = {'render_modes': ['human', 'rgb_array']}

    def __init__(self, render_mode=None, urdf_path="robot_arm.urdf"):
        super().__init__()
        
        if render_mode == "human":
            self.physics_client = p.connect(p.GUI)
        else:
            self.physics_client = p.connect(p.DIRECT)
        
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        
        # Action: кути для 6 joints
        self.action_space = spaces.Box(
            low=-np.pi, high=np.pi, 
            shape=(6,), dtype=np.float32
        )
        
        # Observation: [joints(6), YOLO target(3)]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(9,), dtype=np.float32  # Менше ніж раніше!
        )
        
        self.urdf_path = urdf_path
        self.robot_id = None
        self.yolo_target = np.array([0.0, 0.0, 0.0])  # x, y, confidence
        self.max_steps = 200
        self.current_step = 0
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        p.resetSimulation()
        p.setGravity(0, 0, -9.81)
        
        p.loadURDF("plane.urdf")
        self.robot_id = p.loadURDF(self.urdf_path, [0, 0, 0], useFixedBase=True)
        
        # Випадкові початкові кути
        for joint_id in range(6):
            angle = self.np_random.uniform(-np.pi/2, np.pi/2)
            p.resetJointState(self.robot_id, joint_id, angle)
        
        # Випадковий об'єкт для захоплення
        obj_x = self.np_random.uniform(-0.1, 0.3)
        obj_y = self.np_random.uniform(-0.2, 0.2)
        self.yolo_target = np.array([obj_x, obj_y, 0.9], dtype=np.float32)
        
        self.current_step = 0
        return self._get_obs(), {}
    
    def step(self, action):
        # Застосування дій
        for joint_id in range(6):
            p.setJointMotorControl2(
                self.robot_id, joint_id,
                p.POSITION_CONTROL,
                targetPosition=action[joint_id],
                force=100, maxVelocity=1.0
            )
        
        p.stepSimulation()
        obs = self._get_obs()
        reward = self._compute_reward()
        self.current_step += 1
        
        terminated = self._check_success()
        truncated = self.current_step >= self.max_steps
        
        return obs, reward, terminated, truncated, {}
    
    def _get_obs(self):
        # Поточні позиції joints
        joint_states = np.array([
            p.getJointState(self.robot_id, i)[0] for i in range(6)
        ], dtype=np.float32)
        
        # YOLO target (від зовні!): [x, y, confidence]
        return np.concatenate([joint_states, self.yolo_target])
    
    def _compute_reward(self):
        # Достатність до цілі з координат YOLO
        # Якщо confidence < 0.5, штраф
        if self.yolo_target[2] < 0.5:
            return -1.0  # Об'єкт не виявлено
        
        # Forward kinematics (спрощено)
        ee_pos = self._get_ee_pos()
        target_pos = np.array([self.yolo_target[0], self.yolo_target[1], 0.15])
        distance = np.linalg.norm(ee_pos - target_pos)
        
        reward = -distance * 10
        if distance < 0.05:
            reward += 100.0
        
        return reward
    
    def _get_ee_pos(self):
        """Forward kinematics (спрощено)"""
        ee_state = p.getLinkState(self.robot_id, 5)
        return np.array(ee_state[0])
    
    def _check_success(self):
        return np.linalg.norm(
            self._get_ee_pos() - 
            np.array([self.yolo_target[0], self.yolo_target[1], 0.15])
        ) < 0.05
    
    def close(self):
        p.disconnect()
    
    def update_yolo_observation(self, yolo_data):
        """
        Оновлення спостереження від YOLO
        yolo_data: {"x": float, "y": float, "confidence": float}
        """
        self.yolo_target = np.array([
            yolo_data.get("x", 0.0),
            yolo_data.get("y", 0.0),
            yolo_data.get("confidence", 0.0)
        ], dtype=np.float32)
