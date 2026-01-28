#!/usr/bin/env bash
set -euo pipefail

MEDIA_DIR="$HOME/broadcast_media"

mkdir -p "$MEDIA_DIR"

echo "Setting up dependencies..."

if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y ffmpeg python3-pip
fi

python3 -m pip install --upgrade pip
python3 -m pip install watchdog

echo "Setup complete. Media directory: $MEDIA_DIR"