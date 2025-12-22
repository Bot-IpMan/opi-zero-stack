#!/usr/bin/env bash
set -euo pipefail

DEFAULT_WHEEL_URL="https://github.com/PINTO0309/TensorflowLite-bin/releases/download/v2.14.0.post1/tflite_runtime-2.14.0.post1-cp311-none-linux_armv7l.whl"
DEFAULT_REMOTE_PATH="~/opi-zero-stack/app/wheels/"

usage() {
  cat <<'USAGE'
Usage: copy_tflite_wheel.sh --host USER@IP [options]

Options:
  --host USER@IP        Remote Orange Pi user and host (required unless --download-only).
  --wheel-url URL       Override the default wheel URL.
  --remote-path PATH    Remote destination path (default: ~/opi-zero-stack/app/wheels/).
  --download-only       Only download the wheel locally; skip scp.
  -h, --help            Show this help message.

Examples:
  ./app/scripts/copy_tflite_wheel.sh --host orangepi@192.168.1.101
  ./app/scripts/copy_tflite_wheel.sh --download-only
USAGE
}

host=""
wheel_url="$DEFAULT_WHEEL_URL"
remote_path="$DEFAULT_REMOTE_PATH"
download_only=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host)
      host="$2"
      shift 2
      ;;
    --wheel-url)
      wheel_url="$2"
      shift 2
      ;;
    --remote-path)
      remote_path="$2"
      shift 2
      ;;
    --download-only)
      download_only=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ "$download_only" = false && -z "$host" ]]; then
  echo "Error: --host is required unless --download-only is set." >&2
  usage
  exit 1
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/../.." && pwd)"
wheel_dir="$repo_root/app/wheels"
wheel_name="$(basename "$wheel_url")"

mkdir -p "$wheel_dir"

if [[ ! -f "$wheel_dir/$wheel_name" ]]; then
  echo "Downloading $wheel_name to $wheel_dir"
  curl -L -o "$wheel_dir/$wheel_name" "$wheel_url"
else
  echo "Wheel already exists: $wheel_dir/$wheel_name"
fi

if [[ "$download_only" = false ]]; then
  echo "Copying wheel to $host:$remote_path"
  scp "$wheel_dir/$wheel_name" "$host:$remote_path"
  echo "Done. Wheel copied to $host:$remote_path"
fi
