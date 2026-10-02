# 15 — Private self-hosted deployment

Coolify is supported only when it is self-hosted on company-controlled or
otherwise explicitly private infrastructure.

## Required boundary

- Postgres, Redis, MinIO, API, worker, ASR, optional LLM, TTS, and rendering
  remain inside the private network.
- Public object stores and hosted AI APIs are rejected by the application.
- Model weights are provisioned locally; runtime model downloads are disabled.
- `DEV_BYPASS_AUTH=false` for business data.
- Expose the API only through the approved company VPN/reverse proxy/SSO
  boundary.
- Apply host/VPC/firewall egress-deny rules as defense in depth; allow only
  company-approved internal destinations needed for operations.

Use `docker-compose.coolify.yml` with strong Postgres and MinIO credentials.
The application fails closed if its database, Redis, object storage, or model
endpoint resolves outside the approved private boundary.

## What the compose file enforces

`docker-compose.coolify.yml` matches `infra/compose.yaml`: postgres, redis,
minio, api and worker are attached only to the `private` network, which is
`internal: true` (no route off the host). The `gateway` reverse proxy is the
only service on the routable `edge` network; point the Coolify domain at
`gateway:8080` and keep Coolify itself behind the company VPN/SSO.

Required variables (deploy blocks until set): `POSTGRES_PASSWORD`,
`MINIO_ROOT_PASSWORD`, `AUTH_MODE` (`oidc` with `OIDC_ISSUER`,
`OIDC_AUDIENCE`, `OIDC_JWKS_FILE`/internal `OIDC_JWKS_URL`; or
`trusted-header` with `AUTH_PROXY_SECRET`). Set `BOOTSTRAP_ADMINS` to the
first admin's email. The API runs `python -m app.bootstrap` on start, which
applies the idempotent migrations in `schema/migrations/`.

Verify: `curl https://<host>/health` → `deployment_mode: offline`,
`object_store: private`, `auth` not `unconfigured`, `ok: true`.
