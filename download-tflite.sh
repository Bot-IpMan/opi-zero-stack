#!/usr/bin/env bash
set -euo pipefail

ORANGE_PI_IP=${ORANGE_PI_IP:-192.168.1.101}

WHEELS_DIR="$HOME/robotarm-wheels"
WHEEL_URL="https://github.com/PINTO0309/TensorflowLite-bin/releases/download/v2.14.0.post1/tflite_runtime-2.14.0.post1-cp311-none-linux_armv7l.whl"

mkdir -p "$WHEELS_DIR"

curl -fL "$WHEEL_URL" -o "$WHEELS_DIR/$(basename "$WHEEL_URL")"

ls -lh "$WHEELS_DIR"/tflite_runtime-*.whl

scp "$WHEELS_DIR"/tflite_runtime-*.whl "orangepi@${ORANGE_PI_IP}:~/opi-zero-stack/app/wheels/"

ssh "orangepi@${ORANGE_PI_IP}" "ls -lh ~/opi-zero-stack/app/wheels/"
