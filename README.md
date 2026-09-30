# Grounded Studio

Internal briefing system for recurring work communication.

Drop in a **screen recording**, a **Word/PDF/Notion export**, or an **Excel pack**.
Get back a **reusable briefing object**: narrated walkthrough, slides, chapters, citations, and a chat that is not allowed to invent.

**Hard constraint:** no internal data leaves the company network. Models, storage, transcription, and TTS all run in-house.

This repository is the product spec and implementation contract. Application code comes next; the documents here are the source of truth for what to build.

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
| LLM | vLLM or Ollama, company-approved model | No OpenAI/Anthropic egress |
| Embeddings | local embedding model | RAG without cloud |
| TTS | Piper or Kokoro local | Narration without ElevenLabs |
| Render | Remotion or HTML-to-MP4 (Hyperframes self-hosted) | Deterministic, no Veo |
| Player | first-party web player | Chapters + grounded chat |

Cloud SaaS video models (Veo, Runway, HeyGen, BookWatch-style generators) are **out of scope**.

## Status

House style, both renderers, and the v1 skill compilers live in `apps/engine`.
A local run writes decks and edit lists to `out/demo`:

```bash
PYTHONPATH=apps/engine python -m grounded.demo out/demo
PYTHONPATH=apps/engine python -m grounded.studio out/demo
```

Open http://127.0.0.1:8765. The weekly deck, the leadership deck, and the walkthrough player are on that page. The film is an edit of a source recording: filler and dead air are cut, captions and chapter cards are added, and a click zooms the source pixels. Chat on that page quotes the weekly pack or refuses.
