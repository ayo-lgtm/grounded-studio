# 16 — Railway runtime disabled

Grounded Studio must not receive WBRs, internal documents, recordings,
screenshots, transcripts, prompts, or artifacts on Railway or another
third-party managed application runtime.

The repository keeps a minimal Railway IaC declaration with **zero runtime
resources** so any old linked test project can converge toward no Grounded
Studio application/storage deployment.

The application also rejects known managed-hosting runtime environment markers
while private mode is active.

For real use, deploy on company-controlled infrastructure using
`infra/compose.yaml` or an equivalent private self-hosted stack. Keep
Postgres, Redis, MinIO, ASR, LLM/embeddings, TTS, and rendering inside that
boundary.
