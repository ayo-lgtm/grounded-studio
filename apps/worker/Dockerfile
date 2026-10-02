FROM python:3.12-slim
WORKDIR /app
COPY apps/worker/requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt
COPY infra/install-local-models.sh /tmp/install-local-models.sh
RUN bash /tmp/install-local-models.sh && rm /tmp/install-local-models.sh
COPY apps/engine/grounded ./grounded
COPY apps/worker/worker ./worker
COPY skills ./skills
COPY docs ./docs
COPY README.md ./README.md
ENV HF_HUB_OFFLINE=1 \
    PIPER_BIN=/opt/piper/piper \
    PIPER_MODEL=/opt/piper/en_US-lessac-medium.onnx \
    WHISPER_CACHE=/opt/whisper \
    WHISPER_MODEL=base \
    EGRESS_MODE=offline
CMD ["python", "-m", "worker.main"]
