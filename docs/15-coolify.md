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
3. The S3 staging bucket + Bedrock model access from [14](14-aws-claude.md)
   if you want Transcribe/Polly/Claude. On a non-EC2 box there is no
   instance profile, so create an IAM user with that same policy and keep
   its keys for step 5.

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

AWS + providers (same meaning as [14](14-aws-claude.md)):

| Variable | Value |
|---|---|
| `AWS_REGION` | e.g. `us-east-1` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | IAM user keys; leave empty only on EC2 with an instance profile |
| `CLAUDE_MODEL_ID` | default is fine |
| `TRANS_PROVIDER` | `stub` first; `transcribe` once the bucket exists |
| `TRANS_S3_BUCKET` | staging bucket, e.g. `grounded-transcribe-staging` |
| `TRANS_LANGUAGE` | `en-US` |
| `NARRATION_PROVIDER` | empty first; `polly` to enable voiceover |
| `NARRATION_VOICE` | empty = per-language default |

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
2. `curl https://studio.example.com/health` → `{"ok": true, …}`.
3. Run the end-to-end check from [14](14-aws-claude.md) (briefing → asset →
   transcribe → compile → script → render → chat), swapping the host.
4. Every push to `main` redeploys automatically (disable in the resource
   settings if you want manual releases).

## Notes

- Data lives in the `pgdata` / `miniodata` Docker volumes on the box.
  Snapshot the VPS before real business data, same as [14](14-aws-claude.md).
- `DEV_BYPASS_AUTH` defaults to true for the pilot; wire SSO before
  opening the domain beyond the team.
- If your Coolify version offers a Service-based compose flow instead of
  the Application flow above, the same file works there unchanged.
