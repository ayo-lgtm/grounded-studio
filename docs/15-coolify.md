# 15 — Private self-hosted Coolify deployment

Coolify is supported only when it runs on infrastructure controlled by the
company/private team network. The host must not be a public managed application
runtime receiving sensitive uploads.

## Required boundary

- Postgres, Redis, MinIO, API, worker, local ASR, local model, and local TTS stay
  on the private host/network.
- `GROUND_ALLOW_PUBLIC_EGRESS=false`.
- `DEV_BYPASS_AUTH=false` before real business data is used.
- Do not configure AWS/Bedrock/Transcribe/Polly/OpenAI/Anthropic endpoints.
- Pre-provision model weights locally; runtime model downloads are not allowed.
- Expose the API only through the company VPN/reverse proxy/SSO boundary.

Use `docker-compose.coolify.yml`, set strong Postgres and MinIO passwords, and
configure only internal endpoints. The application will fail closed if a model
or storage endpoint resolves to a public host.
