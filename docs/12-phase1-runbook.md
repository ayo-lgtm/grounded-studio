# 12 — Phase 1 runbook

Application skeleton is in `apps/api` and `apps/worker`.

## What works now

1. Create a briefing
2. Upload a recording into MinIO
3. Enqueue `transcribe` (local faster-whisper with preloaded weights; cloud ASR is not available)
4. Enqueue `compile` — sources are normalized first (cells, blocks, segments). A transcript becomes a walkthrough, an `.xlsx`/`.csv` workbook becomes a WBR/finance/half-year/executive review, and Word/PDF/PowerPoint/Markdown become a leadership or launch deck. Citations are verified against the normalized rows before the script is saved.
5. Citation QA fails closed if a beat has no span
6. Fetch and accept the script
7. Enqueue `render` — cuts the real recording (or renders the deck), writes cell/calculation audits, and adds local Piper narration when `GROUNDED_TTS_PROVIDER=local`
8. Rendered files persist as artifacts (video, captions, deck, storyboard) and download via the artifacts endpoints

The engine also runs without Docker. From the repo root:

```bash
PYTHONPATH=apps/engine python -m grounded.demo out/demo
PYTHONPATH=apps/engine python -m grounded.studio out/demo
```

That compiles every v1 skill against fixtures, fails closed on an empty KPI and on a translated number, writes the decks and the edited films, and serves the review at http://127.0.0.1:8765.

Not yet: SSO. Workbook JSON and `.docx` compile through the worker; an `.xlsx` grid is not parsed.

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

- `AUTH_MODE=oidc` or `trusted-header` (auth fails closed when unset; dev bypass only in `GROUNDED_ENV=development`)
- workbook/document ingest through the API (Phase 3/4)
- EBS snapshots and retention before real business data
- review UI beyond the studio page (accept flow in the browser)
