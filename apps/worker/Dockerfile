FROM python:3.12-slim
WORKDIR /app
COPY apps/worker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/worker/worker ./worker
CMD ["python", "-m", "worker.main"]
