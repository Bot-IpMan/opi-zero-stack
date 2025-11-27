import gymnasium as gym
import numpy as np
import pybullet as p
import pybullet_data
from gymnasium import spaces
import os
import warnings

warnings.filterwarnings('ignore')

class RobotArmEnv(gym.Env):
    """
    6-DOF роборука з YOLO детекцією
    Observation: [joint_positions(6), yolo_target(3)]
    Action: [joint_angles(6)] в радіанах [-π, π]
    """
    metadata = {'render_modes': ['human', 'rgb_array']}

    def __init__(self, render_mode=None, urdf_path=None):
        super().__init__()
        
        print("🚀 Ініціалізація RobotArmEnv...")
        
        # Підключення до PyBullet
        if render_mode == "human":
            self.physics_client = p.connect(p.GUI)
        else:
            self.physics_client = p.connect(p.DIRECT)
        
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        
        # Action space: кути для 6 joints [-π, π]
        self.action_space = spaces.Box(
            low=-np.pi, high=np.pi, 
            shape=(6,), dtype=np.float32
        )
        
        # Observation: [joints(6), yolo_target(3)]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, 
            shape=(9,), dtype=np.float32
        )
        
        # Визначення шляху до URDF
        if urdf_path is None:
            urdf_path = "/workspace/robot_arm.urdf"
            if not os.path.exists(urdf_path):
                urdf_path = "robot_arm.urdf"
            if not os.path.exists(urdf_path):
                urdf_path = os.path.join(
                    os.path.dirname(__file__), 
                    "..", 
                    "robot_arm.urdf"
                )
        
        self.urdf_path = urdf_path
        self.robot_id = None
        self.yolo_target = np.array([0.5, 0.5, 0.9], dtype=np.float32)
        self.max_steps = 200
        self.current_step = 0
        
        print(f"📁 URDF path: {self.urdf_path}")
        print(f"✅ RobotArmEnv ініціалізовано")
        
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        try:
            p.resetSimulation()
            p.setGravity(0, 0, -9.81)
            p.setPhysicsEngineParameter(numSubSteps=1)
            
            # Завантаження підлоги
            p.loadURDF("plane.urdf", [0, 0, -0.1])
            
            # Завантаження робота
            if not os.path.exists(self.urdf_path):
                raise FileNotFoundError(f"URDF не знайдено: {self.urdf_path}")
            
            self.robot_id = p.loadURDF(
                self.urdf_path, 
                [0, 0, 0],
                useFixedBase=True
            )
            
            num_joints = p.getNumJoints(self.robot_id)
            
            # Випадкові початкові позиції (з безпечним діапазоном)
            for joint_id in range(min(6, num_joints)):
                try:
                    # Припинення обмежень для цього joint
                    info = p.getJointInfo(self.robot_id, joint_id)
                    lower_limit = info[8]
                    upper_limit = info[9]
                    
                    # Клipping до безпечного діапазону
                    lower_limit = max(lower_limit, -np.pi)
                    upper_limit = min(upper_limit, np.pi)
                    
                    if lower_limit >= upper_limit:
                        lower_limit = -np.pi / 2
                        upper_limit = np.pi / 2
                    
                    angle = self.np_random.uniform(lower_limit, upper_limit)
                    angle = np.clip(angle, -np.pi, np.pi)
                    
                    p.resetJointState(self.robot_id, joint_id, angle, 0.0)
                except Exception as e:
                    print(f"⚠️  Joint {joint_id}: {e}")
            
            # Випадкова ціль
            self.yolo_target = np.array([
                self.np_random.uniform(0.3, 0.7),
                self.np_random.uniform(0.3, 0.7),
                0.95
            ], dtype=np.float32)
            
            self.current_step = 0
            obs = self._get_obs()
            
            # Перевірка на NaN
            if np.any(np.isnan(obs)):
                print(f"⚠️  NaN в observation, замінюю на нулі")
                obs = np.zeros(9, dtype=np.float32)
            
            return obs, {}
            
        except Exception as e:
            print(f"❌ Помилка в reset: {e}")
            obs = np.zeros(9, dtype=np.float32)
            return obs, {}
    
    def step(self, action):
        try:
            # Клипування дій до безпечного діапазону
            action = np.clip(action, -np.pi, np.pi)
            action = np.nan_to_num(action, nan=0.0, posinf=np.pi, neginf=-np.pi)
            
            num_joints = p.getNumJoints(self.robot_id)
            
            # Застосування дій
            for joint_id in range(min(6, num_joints)):
                try:
                    p.setJointMotorControl2(
                        self.robot_id, joint_id,
                        p.POSITION_CONTROL,
                        targetPosition=float(action[joint_id]),
                        force=100.0,
                        maxVelocity=1.0
                    )
                except Exception as e:
                    print(f"⚠️  Motor control error joint {joint_id}: {e}")
            
            # Крок симуляції
            p.stepSimulation()
            
            obs = self._get_obs()
            reward = self._compute_reward()
            self.current_step += 1
            
            # Перевірка на NaN
            if np.isnan(reward):
                reward = -1.0
            reward = np.clip(reward, -1000, 1000)
            
            terminated = self._check_success()
            truncated = self.current_step >= self.max_steps
            
            return obs, float(reward), terminated, truncated, {}
            
        except Exception as e:
            print(f"❌ Помилка в step: {e}")
            obs = np.zeros(9, dtype=np.float32)
            return obs, -1.0, False, True, {}
    
    def _get_obs(self):
        """Observation: [joint_angles(6), yolo_target(3)]"""
        try:
            num_joints = p.getNumJoints(self.robot_id)
            
            joint_states = []
            for i in range(min(6, num_joints)):
                try:
                    angle = p.getJointState(self.robot_id, i)[0]
                    angle = np.clip(float(angle), -np.pi, np.pi)
                    joint_states.append(angle)
                except:
                    joint_states.append(0.0)
            
            # Паддинг якщо менше 6 joints
            while len(joint_states) < 6:
                joint_states.append(0.0)
            
            joint_states = np.array(joint_states[:6], dtype=np.float32)
            obs = np.concatenate([joint_states, self.yolo_target])
            
            # Перевірка на NaN/Inf
            obs = np.nan_to_num(obs, nan=0.0, posinf=0.0, neginf=0.0)
            obs = np.clip(obs, -10, 10)
            
            return obs
            
        except Exception as e:
            print(f"⚠️  Error in _get_obs: {e}")
            return np.zeros(9, dtype=np.float32)
    
    def _compute_reward(self):
        """Винаграда на основі близькості до цілі"""
        try:
            # Перевірка видимості об'єкта
            if self.yolo_target[2] < 0.5:
                return -1.0
            
            # Forward kinematics
            ee_pos = self._get_ee_pos()
            
            # Ціль в світовій системі координат
            target_world = np.array([
                0.15 + float(self.yolo_target[0]) * 0.25,
                -0.2 + float(self.yolo_target[1]) * 0.4,
                0.15
            ], dtype=np.float32)
            
            # Обчислення відстані
            distance = np.linalg.norm(ee_pos - target_world)
            distance = np.clip(distance, 0, 10)
            
            # Основна винаграда
            reward = -distance * 10.0
            
            # Бонуси
            if distance < 0.05:
                reward += 100.0
            elif distance < 0.1:
                reward += 10.0
            
            reward = np.clip(reward, -1000, 1000)
            return float(reward)
            
        except Exception as e:
            print(f"⚠️  Error in reward: {e}")
            return -1.0
    
    def _get_ee_pos(self):
        """Позиція end-effector"""
        try:
            num_joints = p.getNumJoints(self.robot_id)
            if num_joints > 0:
                ee_state = p.getLinkState(self.robot_id, num_joints - 1)
                pos = np.array(ee_state[0], dtype=np.float32)
                pos = np.clip(pos, -10, 10)
                return pos
        except:
            pass
        
        return np.array([0.0, 0.0, 0.3], dtype=np.float32)
    
    def _check_success(self):
        """Успіх = близько до цілі"""
        try:
            ee_pos = self._get_ee_pos()
            target_world = np.array([
                0.15 + float(self.yolo_target[0]) * 0.25,
                -0.2 + float(self.yolo_target[1]) * 0.4,
                0.15
            ], dtype=np.float32)
            distance = np.linalg.norm(ee_pos - target_world)
            return distance < 0.05
        except:
            return False
    
    def close(self):
        try:
            p.disconnect()
        except:
            pass
