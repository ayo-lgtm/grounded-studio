# 14 — AWS internal runbook (EC2 + Bedrock Claude)

Single EC2 box running `infra/compose.yaml`: Postgres (pgvector), Redis,
MinIO, API, worker. AI comes from Bedrock Claude in-region; transcription
from AWS Transcribe; narration from Amazon Polly.

## Decision record

The original spec (`docs/00-vision.md`, `docs/06-privacy-and-security.md`)
required fully in-house models with no data egress. The business decision
is to run on AWS with Claude instead:

- Prompts (briefing text, chat questions) are processed by Bedrock Claude,
  Transcribe, and Polly **inside the chosen AWS region**. This is egress
  from our VPC to AWS managed services — accepted for the pilot.
- Sources at rest stay in our VPC (EBS volumes, MinIO on instance disk).
- Bedrock does not train on prompts. No Anthropic API key is used.
- Revisit air-gap (vLLM/Ollama/faster-whisper) if a customer or regulator
  requires it. The deterministic engine, QA gates, and `stub` providers
  keep working with no AWS at all.

## Prerequisites (AWS console, one time)

1. EC2 instance (Ubuntu 22.04, t3.large minimum, 100 GB EBS), Docker + plugin.
2. S3 bucket for Transcribe staging, e.g. `grounded-transcribe-staging`.
3. Instance profile with this inline policy (replace region/account/bucket):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["bedrock:InvokeModel"], "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"},
    {"Effect": "Allow", "Action": ["transcribe:StartTranscriptionJob", "transcribe:GetTranscriptionJob"], "Resource": "*"},
    {"Effect": "Allow", "Action": ["s3:PutObject", "s3:GetObject"], "Resource": "arn:aws:s3:::grounded-transcribe-staging/*"},
    {"Effect": "Allow", "Action": ["polly:SynthesizeSpeech"], "Resource": "*"}
  ]
}
```

4. Bedrock console → Model access → enable the Claude model in your region.
5. Security group: inbound 8000/tcp from the company VPN/CIDR only. No public ingress.

## Deploy

```bash
cp .env.example .env   # then set real passwords + TRANS_S3_BUCKET
# enable providers:
#   TRANS_PROVIDER=transcribe
#   NARRATION_PROVIDER=polly
docker compose -f infra/compose.yaml up -d --build
curl http://127.0.0.1:8000/health
```

## End-to-end check

1. `POST /api/v1/briefings` → id
2. `POST /api/v1/briefings/{id}/assets` (kind=recording|workbook|document)
3. `POST /api/v1/briefings/{id}/jobs` type `transcribe` → `succeeded`
4. `.../jobs` type `compile` → `GET .../script` returns beats with citations
5. `POST .../jobs` type `render` → deck.html + walkthrough.mp4 + voiceover.mp3 (when Polly on)
6. `POST /api/v1/briefings/{id}/chat` → grounded answer; refuses off-briefing questions

## Before real business data

- Set `DEV_BYPASS_AUTH=false` only after SSO is wired (API currently fails
  closed with 501 — that is intentional, not a bug).
- Rotate all `change-me` secrets; keep `../.env` off git (already ignored).
- Snapshot EBS; set Postgres/MinIO retention per `docs/06-privacy-and-security.md`.
