#!/usr/bin/env bash
set -Eeuo pipefail

# ---------- утиліти ----------
red(){ printf "\033[31m%s\033[0m\n" "$*"; }
grn(){ printf "\033[32m%s\033[0m\n" "$*"; }
ylw(){ printf "\033[33m%s\033[0m\n" "$*"; }
blu(){ printf "\033[34m%s\033[0m\n" "$*"; }
sec(){ printf "\n\033[1m== %s ==\033[0m\n" "$*"; }

PROJECT_DIR="${PROJECT_DIR:-$PWD}"
COMPOSE_FILE="${COMPOSE_FILE:-$PROJECT_DIR/docker-compose.yml}"
APP_SVC="${APP_SVC:-app}"          # назва сервісу в compose (у вас саме "app")
APP_CONT_NAME="${APP_CONT_NAME:-robot-app}"  # container_name
MOSQ_DIR="${MOSQ_DIR:-$PROJECT_DIR/mosquitto}"
SERIAL_SYMLINK_HOST="${SERIAL_SYMLINK_HOST:-/dev/serial/by-id}"
VIDEO_BYID_DIR="${VIDEO_BYID_DIR:-/dev/v4l/by-id}"
ARDUINO_DEV_ENV="${ARDUINO_DEV_ENV:-/dev/ttyACM0}"  # що в COMPOSE:SERIAL_DEV
CAM_SYM_EXPECT="${CAM_SYM_EXPECT:-usb-_Webcam_C170-video-index0}"

FAILS=0

fail(){ red "✗ $*"; FAILS=$((FAILS+1)); }
ok(){ grn "✓ $*"; }

need(){ command -v "$1" >/dev/null 2>&1 || { fail "Немає утиліти $1"; return 1; }; }

# ---------- 0. Базова система ----------
sec "Система / ядро / доступність /dev/null"
uname -a || true
cat /etc/os-release || true

if [[ ! -c /dev/null ]]; then
  fail "/dev/null не є character device — apt/інші інструменти можуть падати"
  ylw "Фікс (ручний, якщо потрібно): sudo rm -f /dev/null && sudo mknod -m 666 /dev/null c 1 3 && sudo chown root:root /dev/null"
else
  ok "/dev/null виглядає коректно"
fi

# ---------- 1. Docker / Compose ----------
sec "Docker / Compose версії"
if ! need docker; then exit 1; fi
docker version || fail "docker version"
if docker compose version >/dev/null 2>&1; then
  ok "docker compose OK"
else
  fail "docker compose недоступний"
fi

sec "Перевірка синтаксису docker-compose.yml"
if [[ ! -f "$COMPOSE_FILE" ]]; then
  fail "Немає $COMPOSE_FILE"
else
  # Показати найтиповіший YAML-баг: злиплися рядки environment/ports
  if grep -nE 'DUMMY_MODEL=.*ports:' "$COMPOSE_FILE" >/dev/null; then
    fail "Ймовірна помилка YAML: 'DUMMY_MODEL=1    ports:' на одному рядку. Має бути ОКРЕМИМИ рядками."
  fi
  # Офіційна валідація
  if docker compose -f "$COMPOSE_FILE" config >/dev/null 2>&1; then
    ok "docker compose config: синтаксис валідний"
  else
    fail "docker compose config: є помилки — вивід нижче:"
    docker compose -f "$COMPOSE_FILE" config || true
  fi
fi

# ---------- 2. Перевірка директорій Mosquitto ----------
sec "Mosquitto: наявність конфігів/каталогів"
for d in "$MOSQ_DIR/config" "$MOSQ_DIR/data" "$MOSQ_DIR/log"; do
  if [[ -d "$d" ]]; then ok "$d існує"; else fail "$d відсутній"; fi
done
if [[ -f "$MOSQ_DIR/config/mosquitto.conf" ]]; then
  ok "mosquitto.conf існує"
else
  fail "Немає $MOSQ_DIR/config/mosquitto.conf (образ 2.x потребує явний конфіг)"
fi

# ---------- 3. Девайси на хості ----------
sec "USB девайси на хості"
need lsusb && lsusb | egrep -i 'arduino|logitech|046d|082b|2341|2a03' || true

sec "TTY/Video ноди на хості"
ls -l /dev/ttyACM* 2>/dev/null || true
ls -l /dev/video*  2>/dev/null || true

sec "by-id симлінки на хості"
ls -l "$SERIAL_SYMLINK_HOST" 2>/dev/null || true
ls -l "$VIDEO_BYID_DIR" 2>/dev/null || true

# Перевірка правильності симлінків та типів пристроїв
check_char_dev(){
  local path="$1" want_major="$2" label="$3"
  if [[ -e "$path" ]]; then
    local tgt; tgt="$(readlink -f "$path")"
    if [[ -n "$tgt" && -e "$tgt" ]]; then
      local st; st="$(stat -c '%t:%T %F' "$tgt" 2>/dev/null || true)"
      if [[ "$st" == *"character special file"* ]]; then
        # Витягнемо major:minor
        local majmin; majmin="$(stat -c '%t:%T' "$tgt")"
        # hex->dec для major (опціонально), просто покажемо
        ok "$label -> $tgt ($st)"
      else
        fail "$label -> $tgt НЕ є character device (наприклад, може вказувати на vcs/ttyGS0). Перевір udev rule."
      fi
    else
      fail "$label -> розірваний симлінк"
    fi
  else
    fail "$label відсутній"
  fi
}

# Arduino
ARD_SYM="$(ls -1 "$SERIAL_SYMLINK_HOST"/usb-Arduino* 2>/dev/null | head -n1 || true)"
if [[ -n "${ARD_SYM:-}" ]]; then
  check_char_dev "$ARD_SYM" "166" "Arduino by-id"
else
  ylw "Не знайшов Arduino в $SERIAL_SYMLINK_HOST — використаю /dev/ttyACM0 для додаткових перевірок"
  if [[ -e /dev/ttyACM0 ]]; then
    check_char_dev "/dev/ttyACM0" "166" "Arduino /dev/ttyACM0"
  else
    fail "Arduino /dev/ttyACM0 відсутній"
  fi
fi

# Камера
if [[ -e "$VIDEO_BYID_DIR/$CAM_SYM_EXPECT" ]]; then
  check_char_dev "$VIDEO_BYID_DIR/$CAM_SYM_EXPECT" "81" "Camera by-id ($CAM_SYM_EXPECT)"
else
  ylw "Не знайшов $VIDEO_BYID_DIR/$CAM_SYM_EXPECT — спробую /dev/video0"
  if [[ -e /dev/video0 ]]; then
    check_char_dev "/dev/video0" "81" "Camera /dev/video0"
  else
    fail "Камера /dev/video0 відсутня"
  fi
fi

# ---------- 4. Перевірка, що контейнер працює ----------
sec "Compose: стани сервісів"
docker compose -f "$COMPOSE_FILE" ps || true

# ---------- 5. Логи Mosquitto / App ----------
sec "Mosquitto: життєвість"
if docker compose -f "$COMPOSE_FILE" ps mqtt 2>/dev/null | grep -q Up; then
  ok "mqtt контейнер Up"
else
  fail "mqtt контейнер не Up — дивись логи"
  docker compose -f "$COMPOSE_FILE" logs --no-color mqtt | tail -n 80 || true
fi

sec "App: життєвість"
if docker compose -f "$COMPOSE_FILE" ps "$APP_SVC" 2>/dev/null | grep -q Up; then
  ok "app контейнер Up"
else
  fail "app контейнер не Up — дивись логи"
  docker compose -f "$COMPOSE_FILE" logs --no-color "$APP_SVC" | tail -n 120 || true
fi

# ---------- 6. Перевірка healthz і моделі ----------
sec "App: healthz та TFLite сигнатура"
if docker compose -f "$COMPOSE_FILE" ps "$APP_SVC" 2>/dev/null | grep -q Up; then
  if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
    ok "GET /healthz відповідає"
  else
    fail "GET /healthz недоступний на хості — перевір порти/мережу/стан app"
  fi
  # Перевірка 'TFL3' у моделі всередині контейнера без -t
  if docker exec -i "$APP_CONT_NAME" python - <<'PY' 2>/dev/null; then
with open("/app/model.tflite","rb") as f:
  sig = f.read(8)
  print(sig[:4])
PY
  then
    ok "Модель читається всередині контейнера"
  else
    fail "Не вдалось прочитати /app/model.tflite у контейнері"
  fi
else
  ylw "Пропускаю healthz/TFL3 — app не Up"
fi

# ---------- 7. MQTT шлях end-to-end ----------
sec "MQTT pub/sub (всередині mqttc)"
if docker compose -f "$COMPOSE_FILE" ps mqttc 2>/dev/null | grep -q Up; then
  ok "mqttc контейнер Up — зробимо тест"
  # одноразова публікація та коротка підписка
  docker compose -f "$COMPOSE_FILE" exec -T mqttc sh -lc \
    'mosquitto_pub -h mqtt -t diag/ping -m "hello" && mosquitto_sub -h mqtt -C 1 -t diag/ping -v' \
    || fail "mqttc pub/sub тест провалився"
else
  ylw "mqttc не Up — пропускаю mqtt pub/sub"
fi

# ---------- 8. Серійний порт у контейнері ----------
sec "Serial у контейнері (Arduino)"
if docker compose -f "$COMPOSE_FILE" ps "$APP_SVC" 2>/dev/null | grep -q Up; then
  # Перевіряємо, що всередині є вузол і він character
  if docker exec -i "$APP_CONT_NAME" sh -lc 'ls -l /dev/ttyACM0' >/dev/null 2>&1; then
    ok "/dev/ttyACM0 існує у контейнері"
    # швидкий ping
    docker exec -i "$APP_CONT_NAME" python - <<'PY' || true
import serial, time, sys
try:
  s=serial.Serial("/dev/ttyACM0",115200,timeout=1)
  s.reset_input_buffer(); s.reset_output_buffer()
  s.write(b"PING\r\n"); time.sleep(0.15)
  sys.stdout.write("REPLY: "+s.readline().decode(errors="ignore"))
except Exception as e:
  print("SERIAL_ERR:", e)
PY
  else
    fail "/dev/ttyACM0 відсутній у контейнері (devices: у compose?)"
  fi
else
  ylw "Пропускаю serial-тест — app не Up"
fi

# ---------- 9. Поради щодо by-id / udev ----------
sec "Швидка перевірка udev-лінків (антипатерни)"
if [[ -L /dev/arduino ]]; then
  T="$(readlink -f /dev/arduino || true)"
  echo "/dev/arduino -> $T"
  if [[ "$T" =~ /dev/ttyGS0|/dev/vcs ]]; then
    fail "/dev/arduino вказує на $T (не TTY ACM). Udev-правило помилкове."
    cat <<'HINT'
РЕКОМЕНДОВАНІ правила:
  # Arduino Mega 2560 (2341:0042)
  SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0042", \
    SYMLINK+="arduino", GROUP="dialout", MODE="0660"

  # Logitech C170 (046d:082b)
  SUBSYSTEM=="video4linux", ATTRS{idVendor}=="046d", ATTRS{idProduct}=="082b", \
    SYMLINK+="camera-c170-%n", GROUP="video", MODE="0660"
Після змін: sudo udevadm control --reload && sudo udevadm trigger
HINT
  fi
fi

# ---------- 10. Логування Docker ----------
sec "Логування Docker (json-file/local)"
ylw "Якщо бачили помилку \"compression cannot be enabled when max file count is 1\" — поставте logging.options.max-file >= 2 (наприклад 2)."

# ---------- підсумок ----------
sec "ПІДСУМОК"
if (( FAILS > 0 )); then
  red  "Знайдено помилок: $FAILS"
  echo "Прокрутіть вище, у кожному місці є конкретний FIX."
  exit 2
else
  grn "Все ключове виглядає ОК."
fi
