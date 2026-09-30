# 12 — Phase 1 runbook

Application skeleton is in `apps/api` and `apps/worker`.

## What works now

1. Create a briefing
2. Upload a recording into MinIO
3. Enqueue `transcribe` (placeholder segment until faster-whisper is installed)
4. Enqueue `compile` — builds a cited script from transcript segments
5. Citation QA fails closed if a beat has no span
6. Fetch and accept the script

The engine also runs without Docker. From the repo root:

```bash
PYTHONPATH=apps/engine python -m grounded.demo out/demo
PYTHONPATH=apps/engine python -m grounded.studio out/demo
```

That compiles every v1 skill against fixtures, fails closed on an empty KPI and on a translated number, writes the decks and the edited films, and serves the review at http://127.0.0.1:8765.

Not yet: real Whisper, local LLM rewrite of slot text, SSO, and a review UI beyond the rendered deck.

## Run locally

```bash
cp .env.example .env
cd infra
docker compose up --build
```

API: `http://127.0.0.1:8000/health`

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/briefings \
  -H 'content-type: application/json' \
  -d '{"title":"Settings walkthrough","skill_id":"product-walkthrough"}'
```

## Next

- faster-whisper on the GPU worker image
- structured compile against local vLLM/Ollama
- ffmpeg chapter cut + VTT
- a one-page review UI
