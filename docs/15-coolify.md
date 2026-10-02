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
