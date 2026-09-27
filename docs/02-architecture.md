# 02 — Architecture

## Context

```
[Employee browser]
        |  SSO (OIDC)
        v
[Grounded Web]  Next.js
        |
        v
[API]  FastAPI
        |
        +--> Postgres + pgvector
        +--> MinIO
        +--> Redis queue
        +--> Workers (ASR, parse, LLM, TTS, render, index)
        +--> Local model servers (vLLM/Ollama, Whisper, Piper)
```

No worker process is given credentials or routes to OpenAI, Anthropic, Google AI, ElevenLabs, HeyGen, or similar.

## Bounded contexts

1. **Identity** — SSO, sessions, workspaces, RBAC.
2. **Library** — projects, assets, templates.
3. **Ingest** — upload, scan, parse, transcribe.
4. **Compile** — skill router, script generation, citation check, review.
5. **Render** — slides, video, captions.
6. **Serve** — player, signed URLs, chat.
7. **Audit** — append-only events.

## Source object

Everything the system knows about a briefing is a `Briefing`:

```
Briefing
  sources[]          recording | workbook | document
  skill_id
  template_id?       if this is a refresh
  script             beats[] with citations
  artifacts          mp4, vtt, deck, guide
  index              embeddings of sources + script
```

The MP4 is a projection. The script is the source of truth for language. The upload is the source of truth for facts.

## Skill runtime

A skill is a directory:

```
skills/product-walkthrough/
  SKILL.md          contract the LLM must obey
  schema.json       output JSON schema (script)
  qa.py             deterministic citation + numeric checks
```

The compiler:

1. Loads skill + sources + optional previous briefing.
2. Builds a context pack (transcript with times, cell index, outline).
3. Calls local LLM with structured output.
4. Runs `qa.py`. Fail → repair loop (max 2) → send to human if still failing.
5. Stores script version.
6. Renders only accepted beats.

## Why not generative video

Product truth lives in pixels of the recording and cells of the sheet. Image/video generators invent. v1 renderers:

- **Walkthrough:** original video + Ken Burns / zoom-on-click + captions + TTS (or cleaned original voice).
- **Deck:** HTML slides that embed extracted chart images or rendered table snapshots from the actual workbook.
- **Teaser (later):** Hyperframes/Remotion using *screenshots from the recording*, not generated UI.

## Deployment shapes

### Shape A — single GPU workstation (pilot)

Docker Compose on a locked-down Linux box.

- 1× 24GB GPU is enough for Whisper-medium + 7B–14B instruct + Piper.
- Bind MinIO to encrypted disk.
- Firewall: only corp VPN / office subnet.

### Shape B — internal cluster (team)

- API + web on CPU.
- GPU node for models.
- Postgres managed internally.
- Object store on existing company S3-compatible service if it is in-region and private.

## Network policy

| Destination | Allowed |
|---|---|
| Company IdP | yes |
| Internal DNS, NTP, logs | yes |
| Public model APIs | **no** |
| Public telemetry | **no** |
| Outbound to fetch extra context from the live internet during compile | **no** in v1 |

Model weights are pulled once by an admin onto an internal registry, not at job time by workers.

## Failure domains

- LLM down → queue holds, user sees “compiler offline”.
- Whisper down → ingest pauses.
- Render fail → script is kept; retry render only.
- Disk full → reject uploads above remaining quota.

Never silently skip citation checks.
