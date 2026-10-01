import { bucket, defineRailway, image, preserve, project, redis, service, volume } from "railway/iac";

// Test deployment of the grounded-studio pilot stack.
// Secrets (POSTGRES_PASSWORD) are set via the CLI after apply and never
// committed: see docs/16-railway.md. Object storage is a native Railway
// bucket (S3-compatible); MinIO stays the local/Coolify/EC2 default.

export default defineRailway(() => {
  const cache = redis("redis");

  const pgdata = volume("pgdata", { region: "sfo", sizeMB: 1024 });
  const pg = service("pgvector", {
    source: image("pgvector/pgvector:pg16"),
    volumeMounts: {
      "/var/lib/postgresql/data": pgdata,
    },
    env: {
      POSTGRES_USER: "grounded",
      POSTGRES_DB: "grounded",
      POSTGRES_PASSWORD: preserve(),
      PGDATA: "/var/lib/postgresql/data/pgdata",
    },
  });

  const blobs = bucket("blobs", { region: "sjc" });

  const databaseUrl =
    "postgresql+psycopg://grounded:${{pgvector.POSTGRES_PASSWORD}}@${{pgvector.RAILWAY_PRIVATE_DOMAIN}}:5432/grounded";

  const api = service("api", {
    start: "sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'",
    healthcheck: "/health",
    env: {
      DATABASE_URL: databaseUrl,
      REDIS_URL: cache.env.REDIS_URL,
      MINIO_ENDPOINT: "${{blobs.ENDPOINT}}",
      MINIO_BUCKET: "${{blobs.BUCKET}}",
      MINIO_REGION: "${{blobs.REGION}}",
      MINIO_ACCESS_KEY: "${{blobs.ACCESS_KEY_ID}}",
      MINIO_SECRET_KEY: "${{blobs.SECRET_ACCESS_KEY}}",
      AWS_REGION: "us-east-1",
      CLAUDE_MODEL_ID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
      PORT: "8000",
      DEV_BYPASS_AUTH: "true",
      DEV_USER_EMAIL: "dev@internal",
    },
  });

  const worker = service("worker", {
    start: "python -m worker.main",
    env: {
      DATABASE_URL: databaseUrl,
      REDIS_URL: cache.env.REDIS_URL,
      MINIO_ENDPOINT: "${{blobs.ENDPOINT}}",
      MINIO_BUCKET: "${{blobs.BUCKET}}",
      MINIO_REGION: "${{blobs.REGION}}",
      MINIO_ACCESS_KEY: "${{blobs.ACCESS_KEY_ID}}",
      MINIO_SECRET_KEY: "${{blobs.SECRET_ACCESS_KEY}}",
      AWS_REGION: "us-east-1",
      CLAUDE_MODEL_ID: "anthropic.claude-3-5-sonnet-20241022-v2:0",
      TRANS_PROVIDER: "stub",
      TRANS_S3_BUCKET: "",
      TRANS_LANGUAGE: "en-US",
      NARRATION_PROVIDER: "",
      NARRATION_VOICE: "",
    },
  });

  return project("grounded-studio-test", {
    resources: [cache, pgdata, pg, blobs, api, worker],
  });
});
