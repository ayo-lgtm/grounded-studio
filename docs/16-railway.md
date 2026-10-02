# 16 — Railway runtime disabled for sensitive data

Grounded Studio must not receive WBRs, internal documents, recordings, tool
screenshots, transcripts, or other business data on Railway or another
third-party managed application runtime.

The repository keeps a minimal Railway IaC file only to make an existing linked
project converge to **zero runtime resources**. In private mode the application
also detects Railway environment variables and refuses to start.

For real use, deploy the private stack on company-controlled infrastructure
using `infra/compose.yaml` or a private self-hosted equivalent. Keep Postgres,
Redis, MinIO, ASR, LLM, embeddings, TTS, and rendering inside that boundary.
