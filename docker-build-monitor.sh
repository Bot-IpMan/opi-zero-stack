#!/usr/bin/env bash
set -euo pipefail

if ! swapon --show --noheadings | grep -q '.'; then
  echo "ERROR: Swap is not enabled. Please enable swap before running this script." >&2
  exit 1
fi

log_file="build-$(date +%Y%m%d-%H%M%S).log"
start_time=$(date +%s)

format_elapsed() {
  local total_seconds=$1
  local hours=$((total_seconds / 3600))
  local minutes=$(((total_seconds % 3600) / 60))
  local seconds=$((total_seconds % 60))
  printf "%02d:%02d:%02d" "$hours" "$minutes" "$seconds"
}

echo "Cleaning previous Docker resources..."
docker compose down

docker system prune -a --volumes -f

echo "Starting docker compose build in background. Log: $log_file"
docker compose build --no-cache app --progress=plain >"$log_file" 2>&1 &
build_pid=$!

echo "Build PID: $build_pid"

while kill -0 "$build_pid" 2>/dev/null; do
  now=$(date +%s)
  elapsed=$(format_elapsed $((now - start_time)))
  echo ""
  echo "============================================"
  echo "Time: $(date '+%Y-%m-%d %H:%M:%S') | Elapsed: $elapsed"
  echo "--------------------------------------------"
  echo "Memory usage:"
  free -h
  echo "--------------------------------------------"
  if docker ps --format '{{.Names}}' | grep -q '^app$'; then
    echo "Docker stats (app):"
    docker stats app --no-stream || true
  else
    echo "Docker stats (app): container not running"
  fi
  echo "--------------------------------------------"
  echo "Last 50 lines of build log:"
  tail -n 50 "$log_file" 2>/dev/null || true
  echo "============================================"
  sleep 5
done

wait "$build_pid"
build_status=$?

now=$(date +%s)
elapsed=$(format_elapsed $((now - start_time)))

echo ""
echo "============================================"
if [[ $build_status -eq 0 ]]; then
  echo "Build завершено успішно."
else
  echo "Build завершено з помилкою (exit code: $build_status)."
fi

echo "Загальний час: $elapsed"

if [[ -f "$log_file" ]]; then
  echo "--------------------------------------------"
  echo "Повне логування ($log_file):"
  cat "$log_file"
fi

cat <<'RECOMMENDATIONS'
--------------------------------------------
Рекомендації наступних кроків:
1) Перевірити лог на помилки (якщо build завершився з помилкою).
2) Запустити контейнери:
   docker compose up -d
3) Перевірити стан сервісів:
   docker compose ps
4) За потреби переглянути логи:
   docker compose logs -f
RECOMMENDATIONS
