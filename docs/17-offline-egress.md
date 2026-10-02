# 17 — Offline egress

Generation stays on the box. `/health` reports the mode it is actually in.

| `egress` | Meaning |
|---|---|
| `offline` | Chat is local retrieval. Narration is Piper or Kokoro. Transcription is faster-whisper. Object storage host is private. |
| `blocked` | `EGRESS_MODE` is offline (the default) and `MINIO_ENDPOINT` is a public host. Uploads and downloads raise. Nothing is sent. |
| `aws-in-region` | Operator set `EGRESS_MODE=aws-in-region`. Object storage may be public. Chat, TTS, and ASR still do not call Bedrock, Polly, or Transcribe. |

`chat`, `narration`, and `transcription` in the health body stay `retrieval` and `local` in every mode.

## Allowed private endpoints

- Postgres and Redis on localhost, a single-label docker name, RFC1918, or `*.railway.internal`
- MinIO (S3 API) on the same kind of host. Railway service `minio`, volume `miniodata`, endpoint `http://minio.railway.internal:9000`
- Optional `MODEL_BASE_URL` only when the host is private (Ollama or vLLM on the network). Empty means retrieval only. A public host is ignored and the retrieved passage is returned verbatim.

## Refused

Public generative and media APIs are not called, including when credentials exist in the environment:

- Amazon Bedrock and any Anthropic cloud model
- Amazon Polly, ElevenLabs, and any other hosted TTS
- Amazon Transcribe and any hosted ASR
- OpenAI, Google, Veo, Runway, HeyGen, Slides.com, Google Slides, Higgsfield, Scenario
- Hosted Swagger assets (the `/docs` page is a local HTML file)
- Public object storage in offline mode, including Tigris (`*.storageapi.dev`), AWS S3, and `*.railway.app` buckets

`TRANS_PROVIDER` and `NARRATION_PROVIDER` accept `local`. Values `stub`, `transcribe`, `polly`, `aws`, and `elevenlabs` fail the job.

## Weights

The Railway image bakes Piper (`en_US-lessac-medium`) and faster-whisper `base` at build time. Runtime sets `HF_HUB_OFFLINE=1`. A missing weight fails the job. It does not download.
