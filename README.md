# Grounded Studio

Internal briefing system for recurring work communication.

Drop in a **screen recording**, a **Word/PDF/Notion export**, or an **Excel pack**.
Get back a **reusable briefing object**: narrated walkthrough, slides, chapters, citations, and a chat that is not allowed to invent.

**Hard constraint:** no internal data leaves company-controlled infrastructure. In the default `offline` profile, models, storage, transcription and TTS all run in-house. The optional `aws-private` profile may use company-approved Amazon Bedrock / Nova models only through allowlisted private VPC endpoints.

This repository holds the product spec, the skill contracts, and the implementation in `apps/`.

## Why this exists

People at work repeat the same communication every week:

- product owners walk through the same tool
- managers present the same Excel pack
- launches and leadership updates get rebuilt from a Word doc
- global teams need the same talk in another language

Existing tools either send data to a SaaS model or generate cinematic video that is allowed to hallucinate UI and numbers. Grounded Studio does neither.

## Core rule

> A claim in a script, slide, voiceover, or chat answer must cite a source span: a recording timestamp, a spreadsheet cell, or a document paragraph. If it cannot cite, it does not ship.

## Docs

| Doc | What it covers |
|---|---|
| [docs/00-vision.md](docs/00-vision.md) | Product thesis and non-goals |
| [docs/01-trd.md](docs/01-trd.md) | Technical requirements |
| [docs/02-architecture.md](docs/02-architecture.md) | System design, in-house stack |
| [docs/03-user-flows.md](docs/03-user-flows.md) | End-to-end user journeys |
| [docs/04-skills.md](docs/04-skills.md) | Skill catalog and contracts |
| [docs/05-backend-schema.md](docs/05-backend-schema.md) | Data model |
| [docs/06-privacy-and-security.md](docs/06-privacy-and-security.md) | Air-gap, SSO, audit, DLP |
| [docs/07-pipeline.md](docs/07-pipeline.md) | Job pipeline |
| [docs/08-build-plan.md](docs/08-build-plan.md) | Phased build for a job-internal v1 |
| [docs/09-api.md](docs/09-api.md) | HTTP API sketch |
| [docs/13-house-style.md](docs/13-house-style.md) | Locked type, color, and the two renderers |
| [docs/17-offline-egress.md](docs/17-offline-egress.md) | Offline profile and `/health` |
| [docs/18-deployment-profiles.md](docs/18-deployment-profiles.md) | `offline` vs `aws-private` (Bedrock/Nova), providers, grounding with models, egress layers |
| [schema/schema.sql](schema/schema.sql) | Postgres schema |
| [skills/](skills/) | Skill definitions the router loads |

## In-house stack (v1)

| Layer | Choice | Why |
|---|---|---|
| App | Next.js + FastAPI on internal k8s/VM | Familiar, no vendor lock |
| Auth | Company OIDC / SAML | No new identity store |
| DB | Postgres | Relational source graph |
| Files | MinIO (S3 API) on internal disk | Recordings never leave VPC |
| Queue | Redis + workers | Long jobs |
| ASR | faster-whisper (local GPU/CPU) | Transcripts stay inside |
| LLM | none (retrieval), internal vLLM/Ollama, or Amazon Nova via Bedrock in the `aws-private` profile | No OpenAI/Anthropic public egress |
| Embeddings | local hash embedder, or Bedrock (Titan v2 / Nova) in `aws-private` | RAG without public APIs |
| TTS | Piper or Kokoro local | Narration without ElevenLabs |
| Render | Remotion or HTML-to-MP4 (Hyperframes self-hosted) | Deterministic, no Veo |
| Player | first-party web player | Chapters + grounded chat |

Cloud SaaS video models (Veo, Runway, HeyGen, BookWatch-style generators) are **out of scope**.

## Status

Implemented in `apps/`:

* **Two deployment profiles.** `offline` (default) keeps everything on
  private infrastructure. `aws-private` adds explicitly allowlisted Amazon
  Bedrock / Nova models, regions, VPC endpoints and buckets. Everything else
  is refused, in both. See [docs/18](docs/18-deployment-profiles.md).
* **Native sources.** Excel (`.xlsx`/`.xlsm`, formulas evaluated locally when
  uncached), CSV, Word, text-layer PDF, PowerPoint, Markdown/text,
  screenshots (local OCR or Nova), recordings (local faster-whisper), and
  `.zip` packages of these. Cells, rows, blocks and transcript segments are
  persisted with their locations.
* **Executable skills.** Weekly Ops Review / WBR, Finance WBR, Half-Year and
  Executive Business Review (and the rest of the catalog) are runtime
  contracts: accepted inputs, layouts, slide caps and deterministic check ids
  are read from `SKILL.md`, and skill/craft versions and hashes are recorded
  in every script.
* **Grounding.** Every claim cites a cell/range, block/page/slide, or
  timestamp; derived numbers are recomputed from cited cells; citations and
  claims are persisted and verified against the normalized source rows
  before a script ships. Chat answers only from the briefing or says "That
  is not in this briefing."
* **Security.** OIDC or SSO-proxy auth with workspace RBAC on every data
  endpoint; streamed, hashed uploads; private storage only; content-free
  logs; a socket-level egress guard; infra egress-deny for Compose,
  Kubernetes and AWS.

Run the whole studio on your machine (loopback only, synthetic demo briefings):

```bash
pip install -r apps/api/requirements.txt -r apps/worker/requirements.txt -r requirements-test.txt
python scripts/dev_studio.py        # needs postgres + pgvector and redis-server binaries
# open http://127.0.0.1:8765
```

It starts a throwaway Postgres and Redis, an S3-compatible store on 127.0.0.1
standing in for MinIO, the real API (development auth) and worker, and seeds
three synthetic briefings. For a real deployment use `infra/compose.yaml`
([docs/18](docs/18-deployment-profiles.md)); the studio UI design is described
in [docs/19](docs/19-studio-design.md).

Renderer demo (synthetic fixtures):

```bash
PYTHONPATH=apps/engine python -m grounded.demo out/demo
PYTHONPATH=apps/engine python -m grounded.studio out/demo
```

Tests (synthetic data only):

```bash
pip install -r apps/api/requirements.txt -r apps/worker/requirements.txt -r requirements-test.txt
PYTHONPATH=apps/engine GROUNDED_SKILLS_ROOT=skills python -m unittest discover -s apps/engine/tests
PYTHONPATH=apps/worker:apps/engine python -m unittest discover -s apps/worker/tests
PYTHONPATH=apps/api:apps/engine python -m unittest discover -s apps/api/tests
python -m unittest tests/e2e/test_private_stack.py   # needs postgres+pgvector, redis-server, ffmpeg
```
