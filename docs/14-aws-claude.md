# 14 — aws-private profile (Amazon Bedrock / Nova)

The earlier "Bedrock + Claude pilot" path that sent prompts to a public
regional endpoint is gone. Amazon Bedrock and Amazon Nova are supported as
first-class providers **inside the `aws-private` deployment profile only**,
behind explicit allowlists and private AWS networking.

* Profile, provider selection, grounding rules and every egress layer:
  [18 — Deployment profiles](18-deployment-profiles.md).
* Reference infrastructure (VPC without IGW/NAT, VPC endpoints with
  model-restricted policies, least-privilege task role, SSE-KMS bucket,
  encrypted logs): `infra/aws/terraform/`.

What stays the same in aws-private mode:

* Transcription is local faster-whisper and narration is local Piper/Kokoro.
  Amazon Transcribe and Amazon Polly cannot be approved by configuration.
* Every factual statement still needs a valid citation. Nova output is a
  draft that passes deterministic grounding, recomputation and QA gates, or
  it does not ship.
* No static AWS access keys. Credentials come from the task/instance role.

Before using real data: confirm with your security team that the AWS
account, region, Bedrock models, endpoint policies and data classification
are approved for that data. Using AWS does not by itself make a workload
approved for confidential information.
