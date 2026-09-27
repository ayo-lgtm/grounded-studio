# 01 — Technical Requirements Document

**Product:** Grounded Studio
**Deployment:** company network only
**Audience:** internal employees via SSO
**Classification:** internal / confidential. Treat uploaded sources as confidential by default.

## 1. Goals

| ID | Goal |
|---|---|
| G1 | Produce a reusable briefing from a recording, document, or workbook without sending bytes off-network. |
| G2 | Every generated claim cites a source span. |
| G3 | Refresh an existing briefing when the source file changes. |
| G4 | Serve the briefing in a first-party player with grounded Q&A. |
| G5 | Localize a shipped briefing into approved languages without re-recording. |
| G6 | Leave an audit trail of who uploaded, generated, approved, and viewed. |

## 2. Non-goals (v1)

- Public SaaS multi-tenant product
- Generative cinematic video of invented UI
- Codebase-to-demo (`/brag` style)
- Live browser automation that explores unknown products
- Family sharing, App Store, consumer billing
- Training foundation models on customer/employee content

## 3. Functional requirements

### Ingest

- FR-I1 Upload mp4/webm/mov up to a configured cap (default 2 GB, 45 min).
- FR-I2 Upload xlsx, csv, docx, pdf, md.
- FR-I3 Optional second file: knowledge base zip or extra docs attached to the same project.
- FR-I4 Virus scan and MIME sniff before processing.
- FR-I5 Compute SHA-256. Dedup identical blobs.

### Understand

- FR-U1 Transcribe audio with word-level timestamps (local Whisper).
- FR-U2 Detect scene/click cuts via frame diff + optional cursor track.
- FR-U3 Extract workbook sheets, named ranges, and a typed cell index.
- FR-U4 Extract document headings and paragraph IDs.
- FR-U5 Embed chunks locally. Store vectors in Postgres (pgvector) or internal Qdrant.

### Compile

- FR-C1 User selects a skill. Router may suggest one. User confirms.
- FR-C2 Skill writes a script as structured JSON, not free video.
- FR-C3 Citation validator rejects any script line without a valid source pointer.
- FR-C4 Human review UI: edit script, drop a beat, pin a zoom window.
- FR-C5 Render outputs only after accept.

### Outputs

- FR-O1 Chaptered MP4 (H.264) with burned-in or sidecar captions.
- FR-O2 HTML deck (1920×1080 slides) for doc and xlsx skills.
- FR-O3 Step list / SOP markdown.
- FR-O4 Interactive player: chapters, transcript, citation rail, chat.
- FR-O5 Localization job: new voice + captions + translated slides, same citations.

### Recurrence

- FR-R1 A briefing can be cloned as a **template** (skill instance).
- FR-R2 New source file produces a diff: changed cells, changed transcript segments.
- FR-R3 Unchanged beats are reused. Only dirty beats re-render.

### Chat

- FR-Q1 Answers only from retrieved chunks of *this* briefing’s sources.
- FR-Q2 Response includes citations. Player seeks on click.
- FR-Q3 If retrieval is empty or low-confidence, refuse.

## 4. Non-functional

| ID | Requirement |
|---|---|
| NFR-P1 | Default deny egress. Workers have no route to public LLM/TTS APIs. |
| NFR-P2 | TLS in transit, encryption at rest for object store. |
| NFR-P3 | SSO required. No local password store. |
| NFR-P4 | RBAC: owner, editor, viewer, admin. |
| NFR-P5 | Audit log immutable (append-only table). |
| NFR-A1 | Single-VM deploy acceptable for v1 (compose). k8s optional v2. |
| NFR-A2 | Generate a 10-min walkthrough (transcribe + script + render) in < 30 min on one GPU box. |
| NFR-A3 | Player first byte < 2s on internal network. |
| NFR-O1 | Models are version-pinned. Prompt + model id stored on every job. |
| NFR-O2 | Re-run a job with the same inputs + versions → same citations (render timestamps may drift slightly). |

## 5. Compliance assumptions

- Tool is internal-only. Still apply company DLP labels if the source is restricted.
- Do not train on uploads.
- Retention: configurable per workspace (default 365 days, admin-purge).
- No recording of meetings without the uploader being the owner of the file.

## 6. Acceptance tests (v1 gate)

1. Upload a 5-minute silent-plus-voice product recording. Output has chapters that match real screens. Chat cannot name a feature that is not in the transcript or attached doc.
2. Upload last week’s xlsx and this week’s xlsx against the same template. Diff highlights changed KPIs. Script numbers match cells.
3. Upload a 2-page launch doc. Deck has ≤ 12 slides. Every headline traces to a paragraph id.
4. Disconnect the box from the internet. All jobs still complete.
5. A viewer without permission cannot fetch the object URL.
