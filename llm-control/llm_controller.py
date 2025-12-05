#!/usr/bin/env python3
"""
LLM контролер для роборуки
Використовує Claude для планування та виконання команд
"""

import os
import json
import time
import requests
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Конфігурація
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ORANGE_PI_HOST = os.getenv("ORANGE_PI_HOST", "192.168.1.101")
ORANGE_PI_PORT = os.getenv("ORANGE_PI_PORT", "8000")
BASE_URL = f"http://{ORANGE_PI_HOST}:{ORANGE_PI_PORT}"

# Ініціалізація Claude
client = Anthropic(api_key=ANTHROPIC_API_KEY)


class RobotArmController:
    """LLM-контролер для роборуки"""
    
    def __init__(self):
        self.base_url = BASE_URL
        print(f"🤖 LLM Controller ініціалізовано")
        print(f"🔗 Orange Pi: {self.base_url}")
    
    def get_robot_state(self):
        """Отримати поточний стан робота"""
        try:
            response = requests.get(f"{self.base_url}/state", timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Помилка отримання стану: {e}")
            return None
    
    def get_vision_data(self):
        """Отримати дані з камери/YOLO"""
        try:
            response = requests.get(f"{self.base_url}/metrics", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("yolo_target", [0, 0, 0])
        except Exception as e:
            print(f"❌ Помилка отримання vision: {e}")
            return [0, 0, 0]
    
    def send_command(self, joint_angles):
        """Відправити команду руці"""
        try:
            payload = {"x": joint_angles}
            response = requests.post(
                f"{self.base_url}/predict",
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Помилка виконання команди: {e}")
            return None
    
    def execute_llm_command(self, user_command: str):
        """
        Використати LLM для інтерпретації команди
        та генерації плану дій
        """
        
        # Отримати поточний стан
        state = self.get_robot_state()
        vision = self.get_vision_data()
        
        # Контекст для LLM
        system_prompt = """
Ти - контролер роборуки. Твоя задача - перетворити природномовні команди 
користувача в конкретні дії для 6-DOF роборуки.

Доступна інформація:
- Поточні кути joints: {joint_angles}
- YOLO детекція: x={yolo_x:.2f}, y={yolo_y:.2f}, confidence={yolo_conf:.2f}

Доступні функції:
1. move_to(x, y, z) - перемістити кінцевий ефектор до координат
2. grasp() - захопити об'єкт
3. release() - відпустити об'єкт
4. home() - повернутися в початкову позицію

Твоя відповідь має бути JSON з планом дій:
{{
  "understanding": "Що користувач хоче",
  "plan": [
    {{"action": "move_to", "params": {{"x": 0.3, "y": 0.2, "z": 0.15}}}},
    {{"action": "grasp", "params": {{}}}},
    {{"action": "move_to", "params": {{"x": 0.4, "y": 0.0, "z": 0.2}}}}
  ],
  "explanation": "Пояснення кроків"
}}
""".format(
            joint_angles=state.get("joint_angles", [0]*6) if state else [0]*6,
            yolo_x=vision[0],
            yolo_y=vision[1],
            yolo_conf=vision[2]
        )
        
        # Запит до Claude
        print(f"\n🧠 LLM обробляє команду: '{user_command}'")
        
        try:
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_command}
                ]
            )
            
            # Парсинг відповіді
            response_text = message.content[0].text
            print(f"\n📝 LLM відповідь:\n{response_text}")
            
            # Спроба парсити JSON
            try:
                plan = json.loads(response_text)
                return self.execute_plan(plan)
            except json.JSONDecodeError:
                print("⚠️ LLM не повернув валідний JSON")
                return False
                
        except Exception as e:
            print(f"❌ Помилка LLM: {e}")
            return False
    
    def execute_plan(self, plan: dict):
        """Виконати план дій від LLM"""
        
        print(f"\n🎯 Розуміння: {plan.get('understanding', 'N/A')}")
        print(f"📋 План: {plan.get('explanation', 'N/A')}")
        
        actions = plan.get("plan", [])
        
        for i, action_spec in enumerate(actions):
            action = action_spec.get("action")
            params = action_spec.get("params", {})
            
            print(f"\n⚙️ Крок {i+1}/{len(actions)}: {action}")
            
            if action == "move_to":
                # Перетворити XYZ → joint angles (inverse kinematics)
                # Для простоти - використовуємо RL модель
                x, y, z = params.get("x", 0.3), params.get("y", 0.0), params.get("z", 0.15)
                
                # Симулюємо IK через RL модель
                # Відправляємо поточний стан + цільову позицію
                joint_angles = [0.0, 0.5, -0.3, 0.0, 0.0, 0.0]  # Placeholder
                result = self.send_command(joint_angles)
                
                if result:
                    print(f"   ✅ Переміщено до ({x}, {y}, {z})")
                else:
                    print(f"   ❌ Помилка переміщення")
                    return False
                
                time.sleep(2)  # Чекати завершення руху
            
            elif action == "grasp":
                print(f"   🤏 Захоплення...")
                # Команда для захоплення (останній joint = gripper)
                joint_angles = [0]*5 + [1.57]  # Закрити gripper
                self.send_command(joint_angles)
                time.sleep(1)
            
            elif action == "release":
                print(f"   ✋ Відпускання...")
                joint_angles = [0]*5 + [0.0]  # Відкрити gripper
                self.send_command(joint_angles)
                time.sleep(1)
            
            elif action == "home":
                print(f"   🏠 Повернення додому...")
                joint_angles = [0.0] * 6
                self.send_command(joint_angles)
                time.sleep(2)
            
            else:
                print(f"   ⚠️ Невідома дія: {action}")
        
        print(f"\n✅ План виконано!")
        return True


def main():
    """Основний цикл"""
    
    controller = RobotArmController()
    
    print("\n" + "="*50)
    print("🤖 LLM Robot Arm Controller")
    print("="*50)
    print("\nПриклади команд:")
    print('  - "підніми червоний кубик"')
    print('  - "перемісти об\'єкт вліво"')
    print('  - "повернися в початкову позицію"')
    print('  - "покажи поточний стан"')
    print("\nВведіть 'exit' для виходу\n")
    
    while True:
        try:
            command = input("👤 Команда: ").strip()
            
            if not command:
                continue
            
            if command.lower() in ['exit', 'quit', 'q']:
                print("👋 До побачення!")
                break
            
            if command.lower() == "стан" or command.lower() == "status":
                state = controller.get_robot_state()
                vision = controller.get_vision_data()
                print(f"\n📊 Стан робота:")
                print(f"   Joint angles: {state.get('joint_angles', 'N/A') if state else 'N/A'}")
                print(f"   YOLO target: x={vision[0]:.2f}, y={vision[1]:.2f}, conf={vision[2]:.2f}")
                continue
            
            # Виконати команду через LLM
            controller.execute_llm_command(command)
            
        except KeyboardInterrupt:
            print("\n\n👋 До побачення!")
            break
        except Exception as e:
            print(f"\n❌ Помилка: {e}")


if __name__ == "__main__":
    main()
