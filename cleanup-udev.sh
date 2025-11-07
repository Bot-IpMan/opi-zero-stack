#!/bin/bash
set -e

echo "=== Очистка дублікатів udev правил для Arduino ==="

# Видаляємо старі/дублікатні файли
echo "Видаляємо дублікати..."
sudo rm -f /etc/udev/rules.d/60-arduino-mega.rules
sudo rm -f /etc/udev/rules.d/99-arduino-mega.rules
sudo rm -f /etc/udev/rules.d/99-robot.rules

echo "✓ Видалено 3 дублікатні файли"
echo "✓ Залишився лише: /etc/udev/rules.d/99-robot-usb.rules"

# Показуємо, що залишилось
echo ""
echo "=== Вміст /etc/udev/rules.d/99-robot-usb.rules ==="
cat /etc/udev/rules.d/99-robot-usb.rules

# Перезавантажуємо udev
echo ""
echo "=== Перезавантаження udev ==="
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=tty
sudo udevadm trigger --subsystem-match=video4linux

echo "✓ udev правила перезавантажено"

# Чекаємо трохи
sleep 2

# Перевіряємо результат
echo ""
echo "=== Перевірка симлінків ==="
echo "Arduino:"
ls -la /dev/arduino 2>/dev/null || echo "  /dev/arduino не існує (це нормально, якщо Arduino не підключено)"

echo ""
echo "Serial by-id:"
ls -la /dev/serial/by-id/ | grep -i arduino || echo "  Arduino не знайдено"

echo ""
echo "Video by-id:"
ls -la /dev/v4l/by-id/ | grep -i webcam || echo "  Webcam не знайдено"

echo ""
echo "=== ГОТОВО ==="
echo "Тепер перезапустіть Docker:"
echo "  docker compose down"
echo "  docker compose up -d"
