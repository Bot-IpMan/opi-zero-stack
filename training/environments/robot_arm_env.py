# training/environments/robot_arm_env.py

# СТАРЕ (погане):
def _compute_reward(self):
    """Винаграда НЕ працює - агент не вчиться"""
    if self.yolo_target[2] < 0.5:
        return -1.0
    
    ee_pos = self._get_ee_pos()
    target_world = np.array([
        0.15 + float(self.yolo_target[0]) * 0.25,
        -0.2 + float(self.yolo_target[1]) * 0.4,
        0.15
    ])
    
    distance = np.linalg.norm(ee_pos - target_world)
    reward = -distance * 10.0  # ← ПРОБЛЕМА: завжди -1000 до -0
    
    if distance < 0.05:
        reward += 100.0
    elif distance < 0.1:
        reward += 10.0
    
    return float(reward)


# НОВЕ (добре):
def _compute_reward(self):
    """Винаграда яка дійсно вчить агента"""
    try:
        # Якщо об'єкт не видно - велика страта
        if self.yolo_target[2] < 0.5:
            return -10.0
        
        ee_pos = self._get_ee_pos()
        
        # Ціль в світовій системі
        target_world = np.array([
            0.15 + float(self.yolo_target[0]) * 0.25,
            -0.2 + float(self.yolo_target[1]) * 0.4,
            0.15
        ], dtype=np.float32)
        
        # Обчислення відстані
        distance = np.linalg.norm(ee_pos - target_world)
        distance = np.clip(distance, 0, 1.0)  # Макс 1 метр
        
        # НОВИЙ ПОДХІД: Більш адекватна винаграда
        
        # 1. Базова винаграда за наближення (0 до 1)
        proximity_reward = (1.0 - distance)  # ← від 0 до 1
        
        # 2. Бонуси за етапи
        if distance < 0.5:
            proximity_reward += 1.0  # Хороший прогрес
        if distance < 0.2:
            proximity_reward += 1.0  # Дуже близко
        if distance < 0.05:
            proximity_reward += 10.0  # УСПІХ!
        
        # 3. Гладкий градієнт (допомагає навчатися)
        reward = float(proximity_reward)
        
        # Перевірка
        reward = np.clip(reward, -50, 100)
        if np.isnan(reward):
            reward = 0.0
        
        return reward
        
    except Exception as e:
        print(f"⚠️  Reward error: {e}")
        return -1.0
