FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./app
COPY apps/engine/grounded ./grounded
COPY schema/schema.sql ./schema.sql
COPY schema/migrations ./migrations
COPY skills ./skills
COPY docs ./docs
COPY README.md ./README.md
ENV GROUNDED_DEPLOYMENT_MODE=offline HF_HUB_OFFLINE=1
EXPOSE 8000
CMD ["sh", "-c", "python -m app.bootstrap && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers"]
