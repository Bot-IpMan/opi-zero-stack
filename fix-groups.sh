#!/bin/bash
set -e

echo "=== Перевірка груп на хості ==="

# Перевірка GID груп
echo "dialout GID:"
getent group dialout || echo "Група dialout не існує!"

echo ""
echo "video GID:"
getent group video || echo "Група video не існує!"

echo ""
echo "=== Поточні дозволи на пристроях ==="
ls -la /dev/ttyACM0 /dev/video0

echo ""
echo "=== GID всередині контейнера ==="
docker compose exec app sh -c "getent group dialout; getent group video"

echo ""
echo "=== Перевірка, чи застосунок використовує правильні групи ==="
docker compose exec app sh -c "id"

echo ""
echo "=== Перевірка, хто тримає /dev/ttyACM0 ==="
sudo lsof /dev/ttyACM0 2>/dev/null || echo "Ніхто не тримає порт (це добре)"

echo ""
echo "=== Процеси всередині контейнера ==="
docker compose exec app sh -c "ps aux"
