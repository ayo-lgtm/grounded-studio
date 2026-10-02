#!/bin/bash
# Bake Piper and faster-whisper into the image. Runtime stays offline.
set -euo pipefail

PIPER_URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
VOICE_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"

mkdir -p /opt/piper /opt/whisper /tmp/piper-src
curl -fsSL "$PIPER_URL" -o /tmp/piper.tar.gz
tar -xzf /tmp/piper.tar.gz -C /tmp/piper-src
if [ -x /tmp/piper-src/piper/piper ]; then
  cp -a /tmp/piper-src/piper/. /opt/piper/
elif [ -x /tmp/piper-src/piper ]; then
  cp -a /tmp/piper-src/. /opt/piper/
else
  echo "piper binary missing from archive" >&2
  find /tmp/piper-src -maxdepth 3 -type f >&2
  exit 1
fi
chmod +x /opt/piper/piper
curl -fsSL "$VOICE_BASE/en_US-lessac-medium.onnx" -o /opt/piper/en_US-lessac-medium.onnx
curl -fsSL "$VOICE_BASE/en_US-lessac-medium.onnx.json" -o /opt/piper/en_US-lessac-medium.onnx.json
rm -rf /tmp/piper.tar.gz /tmp/piper-src

python - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("base", device="cpu", compute_type="int8", download_root="/opt/whisper")
print("whisper base cached")
PY
