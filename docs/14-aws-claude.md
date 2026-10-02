# 14 — Cloud AI runtime retired

Grounded Studio's runtime policy is **no public data egress**.

Bedrock, AWS Transcribe, Polly, public S3 staging, OpenAI, Anthropic, ElevenLabs,
Runway, HeyGen, and other hosted AI/media providers are not supported runtime
providers for business documents, workbooks, recordings, prompts, transcripts,
or generated artifacts.

Use the private stack with internal Postgres, Redis, MinIO, local
faster-whisper, an optional company-network model endpoint, and local Piper
voice synthesis. Model weights must be provisioned before runtime.

There is no AWS/cloud exception switch in the application egress policy.
