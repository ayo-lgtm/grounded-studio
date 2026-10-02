# Railway test image: api + worker + engine in one image.
# api service start:    uvicorn app.main:app --host 0.0.0.0 --port $PORT
# worker service start: python -m worker.main
# EC2/Coolify keep using apps/api/Dockerfile and apps/worker/Dockerfile.
FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt ./requirements-api.txt
COPY apps/worker/requirements.txt ./requirements-worker.txt
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir -r requirements-api.txt -r requirements-worker.txt
COPY apps/api/app ./app
COPY apps/worker/worker ./worker
COPY apps/engine/grounded ./grounded
COPY skills ./skills
COPY schema/schema.sql ./schema.sql
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
