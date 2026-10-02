# 18 — Deployment profiles, providers and egress controls

Grounded Studio runs in exactly one of two explicit profiles. The profile is
chosen with `GROUNDED_DEPLOYMENT_MODE`; anything else (including the retired
`aws-in-region` value) stops the process at startup.

| | `offline` (default) | `aws-private` |
|---|---|---|
| Document, workbook, PDF, deck, screenshot parsing | local | local |
| Transcription | local faster-whisper | local faster-whisper |
| Narration (TTS) | local Piper / Kokoro | local Piper / Kokoro |
| Inference (polish, chat phrasing, summary) | none, or internal OpenAI-compatible server | none, internal server, or **Amazon Bedrock / Nova** |
| Embeddings | local hash embedder | local, or **Bedrock** (Titan v2 / Nova embeddings) |
| Screenshot text | local OCR (tesseract) | local OCR, or **Nova multimodal** |
| Object storage | internal MinIO | internal MinIO, or **approved private S3** (VPC endpoint, SSE-KMS) |
| Any AWS endpoint | refused | only allowlisted service + region + endpoint + model + bucket |
| Arbitrary internet hosts | refused | refused |

Using AWS does **not** make a workload approved for confidential data. The
account, region, models, networking and data classification for an
`aws-private` deployment must follow your organisation's security and
data-handling requirements. This repository provides the technical controls;
the approval is yours.

## Providers are explicit — no fallback

Every model-backed workload goes through a provider interface
(`apps/engine/grounded/providers/`):

| Interface | Implementations |
|---|---|
| `InferenceProvider` | `LocalInference` (internal vLLM/Ollama/TGI), `BedrockInference` (Converse API; Nova Pro/Lite/Micro/Premier, Nova 2) |
| `EmbeddingProvider` | `LocalHashEmbeddings` (768-d), `BedrockEmbeddings` (Titan Text v2 / Nova multimodal, 256–1024-d) |
| `TranscriptionProvider` | `LocalWhisper` (preloaded weights only) |
| `SpeechProvider` | `LocalPiper` (Piper or Kokoro) |
| `ImageTextProvider` | `LocalOCR` (tesseract), `BedrockImageText` (Nova multimodal, verbatim transcription only) |

Selection (`grounded.providers.registry`):

```
GROUNDED_INFERENCE_PROVIDER      none | local | bedrock        (default none)
GROUNDED_ASSIST_FEATURES         polish, chat, summary          (default empty)
GROUNDED_EMBEDDING_PROVIDER      local-hash | bedrock           (default local-hash)
GROUNDED_TRANSCRIPTION_PROVIDER  local | none                   (default local)
GROUNDED_TTS_PROVIDER            local | none                   (default local)
GROUNDED_IMAGE_TEXT_PROVIDER     none | local-ocr | bedrock     (default none)
```

* Choosing `bedrock` for anything in offline mode is a startup error.
* Retired values (`transcribe`, `aws`, `polly`, `elevenlabs`, `openai`,
  `anthropic`, `stub`) are rejected, never re-mapped.
* If the selected provider fails at call time, the caller keeps its
  deterministic, verbatim result (or fails the job). It never retries on a
  different provider — local never silently becomes cloud, and cloud never
  silently becomes something else.
* Models are configuration: `GROUNDED_BEDROCK_TEXT_MODEL`,
  `GROUNDED_BEDROCK_MULTIMODAL_MODEL`, `GROUNDED_BEDROCK_EMBEDDING_MODEL`.
  Swapping Nova Lite for Nova Pro needs no pipeline change, only the
  allowlist and the variable.

Amazon Transcribe and Amazon Polly are not approvable services in this
codebase (the policy's ceiling is `bedrock-runtime`, `s3`, `sts`, `kms`).
Nova Sonic (speech) uses a bidirectional streaming API that is not wired;
narration and transcription stay local in both profiles.

## Grounding does not change when Nova is used

Nova may analyse, summarise, classify, structure and improve wording. It
may not create facts. Concretely:

1. The deterministic compiler builds a fully cited script first. Every number
   is a claim tied to a cell, block or timestamp; derived numbers carry a
   formula and operand cells.
2. `grounded.assist` lets the selected model *polish* a beat or draft an
   *executive summary* from existing beats only.
3. Each model sentence passes `grounding.check_rewrite` / 
   `assist.check_summary_sentence`: numbers must match the cited beats
   exactly (including the authored surface, e.g. `$4,820,000` stays
   `$4,820,000`), identifiers such as `Q3`/`FY24` may not change, and no
   cause, risk, recommendation, forecast, direction flip, negation flip or
   new entity may appear that the source does not state.
4. QA recomputes every derived claim from its operand cells
   (`grounding.recompute`). A model-proposed calculation is never trusted.
5. The skill contract checks run again (`contracts.run_checks`), then the
   worker verifies every citation and claim against the **persisted**
   normalized rows in Postgres (`verify_against_sources`). Anything that
   fails is dropped or the assist is reverted; the deterministic text ships.
6. Model-assisted beats record `{provider, model_id, source_text}` so the
   artifact shows which sentences a model touched and what they were checked
   against.

Chat answers only from the briefing's beats and its normalized sources
(cells, blocks, transcript segments). A phrased answer must pass the same
rewrite gate, otherwise the verbatim source passage is returned. Anything
the sources do not cover returns **"That is not in this briefing."**

## Egress controls, layer by layer

1. **Policy** (`grounded.policy`). One pure function of the environment.
   Private hosts = loopback, RFC1918/ULA, link-local, single-label service
   names, and the explicit `GROUNDED_INTERNAL_SUFFIXES`. A deny list of
   public AI/storage/CDN/analytics hosts applies in every mode. AWS hosts are
   parsed (`service.region[.vpce].amazonaws.com`) and accepted only in
   aws-private mode when service, region and endpoint are allowlisted;
   regional names count only if `GROUNDED_AWS_PRIVATE_DNS=true` declares that
   interface endpoints with private DNS serve them inside the VPC. Bedrock
   model IDs must match `GROUNDED_BEDROCK_MODELS` exactly; S3 buckets must
   match `GROUNDED_OBJECT_BUCKETS`.
2. **Startup gate** (`policy.assert_runtime`). API and worker refuse to
   start on an unknown mode, the retired public-egress switch, a third-party
   hosted runtime (Railway, Vercel, Render, Fly, Heroku, Netlify), a public
   database/Redis/model host, or an inconsistent provider selection.
3. **Clients**. The object store checks endpoint *and* bucket before any
   client exists, even an injected one. Bedrock checks model/region/endpoint
   before building the client and re-checks the endpoint boto3 resolved.
   Static long-lived AWS keys are refused (role credentials only). Generic
   HTTP exists in exactly one module (`grounded.net`), which allows only
   private hosts, ignores proxy environment variables and refuses redirects.
4. **Socket guard** (`grounded.guard`). Installed at startup in API and
   worker. Every `connect`/`sendto` to a public IP raises unless that IP was
   resolved from a policy-approved AWS hostname. This catches any library
   or bug that bypasses layer 3.
5. **Infrastructure** — the layer an application bug cannot change:
   * Compose (`infra/compose.yaml`, `docker-compose.coolify.yml`): data
     services, API and worker live only on an `internal: true` network with
     no route off the host. A stateless `gateway` reverse proxy is the only
     container on a routable network.
   * Kubernetes (`infra/k8s/networkpolicy.yaml`): default-deny ingress and
     egress, DNS to kube-dns only, intra-namespace traffic, ingress from the
     SSO proxy namespace, and (aws-private) HTTPS to the endpoint subnets.
   * AWS (`infra/aws/terraform/`): a VPC with **no internet gateway and no
     NAT**, private subnets only, security groups without `0.0.0.0/0`
     egress, interface endpoints for `bedrock-runtime`, `sts`, `kms`, `logs`,
     `ecr.api`, `ecr.dkr`, an S3 gateway endpoint restricted to the
     artifacts bucket, a Bedrock endpoint policy allowing only the approved
     model ARNs, an IAM task role scoped to those models and that bucket
     with `aws:SourceVpce` conditions, a private SSE-KMS bucket that denies
     non-TLS, non-VPCE and unencrypted writes, KMS-encrypted CloudWatch log
     groups, and VPC flow logs for rejected traffic. Bedrock model
     invocation logging (which would store prompts) is deliberately not
     enabled.
6. **CI** (`.github/workflows/engine-tests.yml`): a static privacy scan
   (`test_privacy_scan.py`) fails on public AI/ASR/TTS endpoints, Transcribe
   or Polly calls, cloud staging stores, CDNs/remote fonts, telemetry SDKs,
   runtime model downloads, and generic HTTP outside `grounded.net`; profile
   tests cover both modes; infra tests fail if the internal network,
   default-deny policy or no-IGW/no-NAT design is weakened; `terraform
   validate` runs on the reference module.

## Logging

`grounded.logsafe` logs ids, counts, durations, provider names and error
*classes*. Document text, cell values, transcript text, prompts, model
output, filenames and exception messages are never logged; SDK wire loggers
(botocore, urllib3, s3transfer) are pinned to WARNING. The end-to-end test
plants a synthetic marker in every source and fails if it appears in logs.

## aws-private configuration example

```
GROUNDED_DEPLOYMENT_MODE=aws-private
GROUNDED_AWS_REGIONS=us-east-1
GROUNDED_AWS_SERVICES=bedrock-runtime,s3
GROUNDED_AWS_PRIVATE_DNS=true
GROUNDED_BEDROCK_MODELS=amazon.nova-pro-v1:0,amazon.nova-lite-v1:0,amazon.titan-embed-text-v2:0
GROUNDED_INFERENCE_PROVIDER=bedrock
GROUNDED_ASSIST_FEATURES=polish,chat,summary
GROUNDED_BEDROCK_TEXT_MODEL=amazon.nova-pro-v1:0
GROUNDED_BEDROCK_MULTIMODAL_MODEL=amazon.nova-lite-v1:0
GROUNDED_EMBEDDING_PROVIDER=bedrock
GROUNDED_BEDROCK_EMBEDDING_MODEL=amazon.titan-embed-text-v2:0
GROUNDED_IMAGE_TEXT_PROVIDER=bedrock
GROUNDED_OBJECT_BUCKETS=<terraform output bucket>
GROUNDED_OBJECT_KMS_KEY=<terraform output key ARN>
MINIO_ENDPOINT=https://s3.us-east-1.amazonaws.com
MINIO_BUCKET=<terraform output bucket>
# no AWS_ACCESS_KEY_ID: the ECS task / IRSA role provides session credentials
```

Cross-region inference profiles (`us.amazon.nova-pro-v1:0`) route requests
to other regions; they are accepted only if listed exactly, and the Terraform
endpoint/IAM policies must then name the inference-profile ARNs. Prefer
in-region foundation-model IDs unless your policy approves cross-region
routing.
