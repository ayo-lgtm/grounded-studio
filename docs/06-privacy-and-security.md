# 06 — Privacy and security (in-house)

This product only exists if security will let employees use it.

## Egress

Workers have no default route to the public internet. Allowlist: internal IdP, internal artifact registry, internal syslog, and in-network Postgres, Redis, and MinIO. Model weights are preloaded. Compile-time web research is disabled. Bedrock, Polly, Transcribe, and public object stores fail closed. `/health` reports `offline` or `blocked`. See [17](17-offline-egress.md).

## Identity and ACL

OIDC/SAML against company IdP. Workspace RBAC. Object URLs are short-lived signed MinIO links. Chat uses the same ACL as the briefing.

## Encryption and secrets

TLS internally as required by the company mesh. MinIO encryption with a company-managed key. No employee OpenAI keys in `.env`.

## Audit

Log login, upload, generate, accept script, publish, download, share, delete, chat.

## Malware

Scanner on ingest. xlsx parsed as values only. Macros not executed.

## Training

v1 has no fine-tune job type. Uploads are never used to train a model without a separate Legal + Security change.

## Residual risk

A local LLM can still invent if citation QA is bypassed. QA is blocking and human accept is required. Privileged admins on the GPU box can read storage; that is existing PAM, not a new exception.

## What we tell InfoSec

Grounded Studio is a self-hosted compiler. Media and documents stay on company object storage. Speech-to-text, language models, embeddings, and TTS run on company GPUs. There is no call to a public generative API at job time. Access is SSO + workspace ACL. Every published sentence is citation-checked and human-accepted.
