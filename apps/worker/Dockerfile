FROM python:3.12-slim
WORKDIR /app
COPY apps/worker/requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir -r requirements.txt
COPY apps/engine/grounded ./grounded
COPY apps/worker/worker ./worker
CMD ["python", "-m", "worker.main"]
