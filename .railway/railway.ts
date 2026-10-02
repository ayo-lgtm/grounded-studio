import { defineRailway, image, preserve, project, redis, service, volume } from "railway/iac";

// Offline test stack. Object storage is in-project MinIO on miniodata,
// not the public Tigris bucket. Secrets are set with the CLI
// (POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD) and never committed.

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

  const miniodata = volume("miniodata", { region: "sfo", sizeMB: 5120 });
  // elestio/minio:latest runs as root and can write a fresh Railway volume at
  // /data. Docker Hub no longer serves minio/minio or bitnami/minio:latest.
  // Bitnami UID 1001 cannot write root-owned Railway mounts; bitnamilegacy
  // only boots with the volume omitted. Quay pulls of official MinIO are off.
  const minio = service("minio", {
    source: image("elestio/minio:latest"),
    start: "minio server /data --address :9000 --console-address :9001",
    healthcheck: "/minio/health/live",
    volumeMounts: {
      "/data": miniodata,
    },
    env: {
      MINIO_ROOT_USER: "grounded",
      MINIO_ROOT_PASSWORD: preserve(),
    },
  });

  const databaseUrl =
    "postgresql+psycopg://grounded:${{pgvector.POSTGRES_PASSWORD}}@${{pgvector.RAILWAY_PRIVATE_DOMAIN}}:5432/grounded";
  const minioEndpoint = "http://${{minio.RAILWAY_PRIVATE_DOMAIN}}:9000";

  const shared = {
    DATABASE_URL: databaseUrl,
    REDIS_URL: cache.env.REDIS_URL,
    MINIO_ENDPOINT: minioEndpoint,
    MINIO_BUCKET: "grounded",
    MINIO_REGION: "us-east-1",
    MINIO_ACCESS_KEY: "grounded",
    MINIO_SECRET_KEY: "${{minio.MINIO_ROOT_PASSWORD}}",
    EGRESS_MODE: "offline",
    MODEL_BASE_URL: "",
    MODEL_NAME: "local-instruct",
  };

  const api = service("api", {
    start: "sh -c 'uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'",
    healthcheck: "/health",
    env: {
      ...shared,
      PORT: "8000",
      DEV_BYPASS_AUTH: "true",
      DEV_USER_EMAIL: "dev@internal",
    },
  });

  const worker = service("worker", {
    start: "python -m worker.main",
    env: {
      ...shared,
      TRANS_PROVIDER: "local",
      TRANS_LANGUAGE: "en-US",
      NARRATION_PROVIDER: "local",
      WHISPER_MODEL: "base",
      WHISPER_CACHE: "/opt/whisper",
      PIPER_BIN: "/opt/piper/piper",
      PIPER_MODEL: "/opt/piper/en_US-lessac-medium.onnx",
      HF_HUB_OFFLINE: "1",
    },
  });

  return project("grounded-studio-test", {
    resources: [cache, pgdata, pg, miniodata, minio, api, worker],
  });
});
