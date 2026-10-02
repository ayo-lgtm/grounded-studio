# Combined image: api + worker + engine. Local weights are baked at build time.
# api start:    uvicorn app.main:app --host 0.0.0.0 --port $PORT
# worker start: python -m worker.main
FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt ./requirements-api.txt
COPY apps/worker/requirements.txt ./requirements-worker.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg fonts-dejavu-core curl ca-certificates tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements-api.txt -r requirements-worker.txt
COPY infra/install-local-models.sh /tmp/install-local-models.sh
RUN bash /tmp/install-local-models.sh && rm /tmp/install-local-models.sh
COPY apps/api/app ./app
COPY apps/worker/worker ./worker
COPY apps/engine/grounded ./grounded
COPY schema/schema.sql ./schema.sql
COPY schema/migrations ./migrations
COPY skills ./skills
COPY docs ./docs
COPY README.md ./README.md
ENV HF_HUB_OFFLINE=1 \
    PIPER_BIN=/opt/piper/piper \
    PIPER_MODEL=/opt/piper/en_US-lessac-medium.onnx \
    WHISPER_CACHE=/opt/whisper \
    WHISPER_MODEL=base \
    GROUNDED_DEPLOYMENT_MODE=offline \
    TRANSFORMERS_OFFLINE=1
CMD ["sh", "-c", "python -m app.bootstrap && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
