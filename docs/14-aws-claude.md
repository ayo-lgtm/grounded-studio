# 14 — Retired cloud-provider runbook

This runbook is intentionally retired.

Grounded Studio's current security contract is **no public data egress**. Bedrock,
AWS Transcribe, Polly, public S3 staging, Anthropic/OpenAI APIs, and other managed
AI services are not valid runtime providers for business documents, workbooks,
recordings, prompts, transcripts, or generated artifacts.

Use the private stack in `infra/compose.yaml` with:

- internal Postgres;
- internal Redis;
- internal MinIO;
- a pre-provisioned local faster-whisper model;
- an optional internal-only LLM endpoint;
- a pre-provisioned local Piper voice model.

The runtime enforces this contract: public endpoints are rejected and known
third-party hosted environments such as Railway are refused in private mode.
