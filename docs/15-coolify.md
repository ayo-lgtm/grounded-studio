# 15 — Coolify deploy (open-source self-host)

Same pilot stack as [14](14-aws-claude.md), deployed through
[Coolify](https://github.com/coollabsio/coolify) (open-source, self-hosted
PaaS) instead of raw `docker compose` on EC2. One file at the repo root —
[docker-compose.coolify.yml](../docker-compose.coolify.yml) — holds postgres,
redis, minio, api, and worker. Coolify builds the images, injects env vars,
routes the api domain through its proxy, and redeploys on every push.

## What you need

1. A VPS (4 GB RAM minimum, 100 GB disk) with SSH access. Any provider works;
   the box does not have to be EC2.
2. A domain (or subdomain) pointed at the box for the api, e.g.
   `studio.example.com`.
3. No public model keys. Chat, transcription, and narration stay on the box.
   See [17](17-offline-egress.md). Doc [14](14-aws-claude.md) is a closed pilot record.

## Install Coolify (one time, on the box)

Follow the official [self-hosted setup](https://coolify.io/docs/start-with-self-hosted)
(the installer brings Docker with it), open the dashboard, and connect your
GitHub account so Coolify can read this repo (private repos work).

## Create the resource

1. **New Resource → Application**, source = this GitHub repo, branch `main`.
2. Build pack: **Docker Compose**.
3. Base Directory: `/` (repo root). Compose Location:
   `docker-compose.coolify.yml`.
4. Save and let Coolify parse the file. It creates every `${VAR}` under
   **Environment Variables**.

## Set variables

Required (deploy is blocked while these are empty):

| Variable | Value |
|---|---|
| `POSTGRES_PASSWORD` | long random string |
| `MINIO_ROOT_PASSWORD` | long random string (app keys reuse it automatically) |

Offline profile (defaults in the compose file):

| Variable | Value |
|---|---|
| `EGRESS_MODE` | `offline` |
| `TRANS_PROVIDER` | `local` (faster-whisper). `stub`, `transcribe`, and `aws` fail the job |
| `NARRATION_PROVIDER` | `local` (Piper or Kokoro). `polly` and `elevenlabs` fail the job |
| `MODEL_BASE_URL` | empty, or a private host only |

Do not set `CLAUDE_MODEL_ID` or AWS keys for chat, TTS, or ASR. MinIO is the `minio` service on the compose network (`http://minio:9000`).

Everything else (`POSTGRES_USER`, `MINIO_BUCKET`, …) keeps its default
unless you change it in the UI.

## Expose the API

1. Open the resource → **Domains**, add yours with the container-port
   suffix: `https://studio.example.com:8000`. The public request still
   uses 443; the suffix tells the proxy the api listens on 8000.
2. No `ports:` are published by design — postgres, redis, minio, and the
   worker stay on the private stack network. The proxy joins it automatically.

## Deploy and verify

1. Press **Deploy** and watch the log: images build, postgres runs
   `schema.sql`, api + worker start.
2. `curl https://studio.example.com/health` → `egress` is `offline`, `chat` is `retrieval`, `object_store` is `private`.
3. Run the end-to-end check from [16](16-railway.md) (briefing → asset →
   local transcribe → compile → script → render → chat), swapping the host.
4. Every push to `main` redeploys automatically (disable in the resource
   settings if you want manual releases).

## Notes

- Data lives in the `pgdata` / `miniodata` Docker volumes on the box.
  Snapshot the VPS before real business data, same as [14](14-aws-claude.md).
- MinIO is `elestio/minio:latest`. Docker Hub no longer serves `minio/minio`
  or `bitnami/minio:latest`. The compose command is
  `minio server /data --address :9000 --console-address :9001`.
  The Railway volume permission pitfall (Bitnami UID 1001) is in [16](16-railway.md).
- `DEV_BYPASS_AUTH` defaults to true for the pilot; wire SSO before
  opening the domain beyond the team.
- If your Coolify version offers a Service-based compose flow instead of
  the Application flow above, the same file works there unchanged.
