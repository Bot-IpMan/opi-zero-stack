#!/usr/bin/env bash
set -Eeuo pipefail

sec(){ printf "\n\033[1m== %s ==\033[0m\n" "$*"; }
ok(){ printf "\033[32m✓ %s\033[0m\n" "$*"; }
warn(){ printf "\033[33m! %s\033[0m\n" "$*"; }
fail(){ printf "\033[31m✗ %s\033[0m\n" "$*"; }

need(){ command -v "$1" >/dev/null 2>&1 || { fail "Відсутня утиліта $1"; return 1; }; }

sec "Базова система"
uname -a
cat /etc/os-release 2>/dev/null || warn "Немає /etc/os-release"

sec "CPU та інструкції"
if need lscpu; then
  lscpu
else
  warn "lscpu недоступний; покажу /proc/cpuinfo flags"
fi
# Унікальні flags для швидкої перевірки SSE4.1
if [[ -r /proc/cpuinfo ]]; then
  FLAGS=$(awk -F': ' '/^flags[[:space:]]*:/ {print $2; exit}' /proc/cpuinfo || true)
  if [[ -n "$FLAGS" ]]; then
    echo "flags: $FLAGS"
    if grep -qw sse4_1 <<<"$FLAGS"; then
      ok "CPU заявляє підтримку sse4_1"
    else
      fail "CPU НЕ показує sse4_1 у flags"
    fi
  else
    warn "Не зміг прочитати flags з /proc/cpuinfo"
  fi
else
  warn "/proc/cpuinfo недоступний"
fi

sec "Віртуалізація"
if command -v systemd-detect-virt >/dev/null 2>&1; then
  systemd-detect-virt || true
elif need lscpu; then
  lscpu | grep -i 'Virtualization'
else
  warn "Не можу визначити тип віртуалізації"
fi

sec "Python / TensorFlow"
if need python3; then
  python3 --version
  if python3 -m pip --version >/dev/null 2>&1; then
    python3 -m pip show tensorflow tensorflow-cpu 2>/dev/null || warn "TensorFlow не знайдено через pip show"
  else
    warn "pip для python3 недоступний"
  fi

  python3 - <<'PY'
import json, platform, sys
print(f"Python executable: {sys.executable}")
print(f"Platform: {platform.platform()}")
try:
    import tensorflow as tf
    print(f"TensorFlow version: {tf.__version__}")
    build = tf.sysconfig.get_build_info()
    # Ключові build-прапорці, що показують інструкції CPU
    keys = ["cpu_compiler_flags", "gcc_version", "target_cpu_features", "is_cuda_build", "is_rocm_build"]
    for k in keys:
        if k in build:
            print(f"{k}: {build[k]}")
    try:
        print("compile_flags:", tf.sysconfig.get_compile_flags())
        print("link_flags:", tf.sysconfig.get_link_flags())
    except Exception as e:
        print("Не зміг отримати compile/link flags:", e)
    try:
        devices = tf.config.list_physical_devices()
        print("Physical devices:", devices)
    except Exception as e:
        print("Не зміг отримати список пристроїв:", e)
except Exception as e:
    print("Не вдалося імпортувати TensorFlow або витягти build info:", e)
PY
else
  fail "python3 недоступний"
fi

sec "Docker/контейнер (перевірка розрізання інструкцій)"
if command -v docker >/dev/null 2>&1; then
  docker info --format '{{.OperatingSystem}} | Default runtime: {{.DefaultRuntime}}' || true
  docker version || true
else
  warn "docker недоступний; пропускаю"
fi

sec "Makefile ціль export"
if [[ -f Makefile ]]; then
  grep -n '^export:' -A3 Makefile || true
else
  warn "Makefile відсутній"
fi

echo "\nГотово: зберіть цей вивід і надішліть для діагностики SSE4.1/TensorFlow."

