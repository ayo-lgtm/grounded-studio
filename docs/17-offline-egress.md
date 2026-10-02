# 17 — Offline profile and `/health`

`GROUNDED_DEPLOYMENT_MODE=offline` is the default. Full design, both
profiles and every enforcement layer: [18](18-deployment-profiles.md).

`GET /health` (unauthenticated, content-free) reports the posture the
process is actually running with:

| field | values |
|---|---|
| `deployment_mode` | `offline` or `aws-private` |
| `egress` | the mode, or `blocked` when the object store is public/unapproved, or `misconfigured` when the policy cannot load (e.g. the retired `aws-in-region`) |
| `object_store` | `private`, `aws-private-s3`, or `public-refused` |
| `providers` | the explicit selection per workload (inference, embedding, transcription, tts, image_text, models) |
| `chat` | `retrieval` or `retrieval+validated-phrasing` |
| `auth` | `oidc`, `trusted-header`, `dev` (development only) or `unconfigured` |

`ok` is false when the database is down, storage is refused, providers are
misconfigured, or auth is unconfigured.

## Offline guarantees

* No AWS endpoint, Bedrock model or public host is reachable through the
  policy; the socket guard blocks any public IP; compose puts API, worker
  and data services on an `internal: true` network.
* Chat is retrieval over the briefing's own sources. An internal
  OpenAI-compatible server (vLLM/Ollama) may phrase answers only when
  `GROUNDED_INFERENCE_PROVIDER=local` and `GROUNDED_ASSIST_FEATURES`
  includes `chat`; its output passes the grounding gate or is discarded.
* Transcription is faster-whisper with `local_files_only` and
  `HF_HUB_OFFLINE=1`; narration is Piper/Kokoro. Missing weights fail the
  job; nothing downloads at runtime.
* The worker image bakes Piper `en_US-lessac-medium` and whisper `base` at
  build time (`infra/install-local-models.sh`, which accepts an internal
  mirror via `PIPER_URL`, `VOICE_BASE`, `WHISPER_LOCAL_DIR`).
* `/docs` is a local HTML page; Swagger/ReDoc/OpenAPI are disabled; the
  room UI and decks load no remote scripts, styles or fonts.
