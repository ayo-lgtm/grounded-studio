# 04 — Skill catalog

A **skill** is a versioned playbook: required inputs, story beats, which locked layouts it may use, and QA.

Two renderers serve every v1 skill. The recording editor cuts a real capture. The deck renderer fills masters in `apps/engine/grounded/house.py`. A skill does not choose type, color, or spacing.

v1 ships **8 skills**. v1.5 adds **4**. Do not invent more until these work.

## Router

Input: MIME types + optional user hint + filename.

| Signals | Suggested skill |
|---|---|
| video/* | `product-walkthrough` |
| video/* + “changelog” in attached doc | `feature-delta` |
| xlsx/csv | `weekly-ops-review` |
| docx/pdf/md + user chose leadership | `leadership-brief` |
| docx/pdf/md + launch/announce words | `launch-announcement` |
| video/* + user chose training | `sop-training` |
| existing briefing + target_lang | `localize` |
| any published briefing | `grounded-qa` (layer, always on) |

User can override.

## v1 skills (build these)

1. `product-walkthrough` — real recording → chaptered demo. Never invent UI.
2. `feature-delta` — parent briefing + new clip/changelog.
3. `leadership-brief` — written doc → sparse leadership deck.
4. `launch-announcement` — launch writeup → announcement deck.
5. `weekly-ops-review` — workbook → cited KPI briefing. Empty cells fail closed.
6. `sop-training` — recording/doc → numbered SOP.
7. `localize` — sibling language, same citations, locked numbers.
8. `grounded-qa` — chat that refuses on miss.

## v1.5 (later)

9. `path-replay` — Playwright on allowlisted internal staging only.
10. `exec-narrative` — longer memo → deck + appendix.
11. `launch-teaser` — 15–25s from recording screenshots, local render.
12. `glossary-apply` — company term lock.

Full contracts live under `skills/*/SKILL.md`.

## Library expansion (skills added for breadth)

The v1 list and the v1 router table above are unchanged. This section indexes additional playbooks. They are not a claim that the v1 router already dispatches them.

Every file in this expansion is **offline and local only**. `offline: true` is required. Workers must not call a public HTTP API, a SaaS slide or video product, or a cloud model. Allowed tools are local FFmpeg, the recording editor, the deck renderer in `apps/engine/grounded/house.py`, local faster-whisper, local Piper or Kokoro, local OCR, local Playwright against an on-disk allowlist of internal hosts, and Postgres, MinIO, and Redis on localhost or the company network. Public internet egress is forbidden. A self-hosted service is allowed only when it never leaves that network.

A claim still needs a citation (`recording`, `workbook`, or `document`). Empty required numbers fail closed. Skills pick a layout id from the locked set (`cover`, `big-number`, `versus-target`, `movers`, `risk`, `ask`, `statement`, `step`). They do not set color, type, or spacing. Narrative is planned before slides. One idea per slide. Action titles are corridor sentences made of cited tokens. Video hooks, trims, zooms, and captions use source timestamps and source pixels.

v1.5 names `path-replay`, `exec-narrative`, and `launch-teaser` stay in the list above. The expansion specifies them as `allowlisted-path-replay`, `exec-narrative-deck`, `launch-teaser-cut`, and `launch-teaser-still-deck` so the v1.5 lines are not overwritten.

### Video — recording editor

| Skill | Summary |
|---|---|
| `chaptered-demo-cut` | Cut a real screen recording into timeline-ordered chapters that follow the spoken task changes. |
| `dead-air-trim` | Remove measured silence from a real recording while keeping every spoken claim and its timestamps. |
| `click-zoom-edit` | Punch in on a real click by cropping source pixels around a detected click box. |
| `caption-burn-in` | Burn captions that are the spoken line, timed to the local transcript, onto a real cut. |
| `chapter-card-overlay` | Insert a short title card before each chapter using the label read off the capture. |
| `multi-clip-concat` | Join accepted clips in cited order into one recording-editor timeline. |
| `highlight-reel-from-chapters` | Assemble a reel from chapters a human already marked keep, in their original order. |
| `local-tts-duck-overlay` | Lay a local Piper or Kokoro reading of an accepted script line under a ducked source bed. |
| `side-by-side-before-after` | Show two cited captures in one frame, before on the left and after on the right, using only their pixels. |
| `accessibility-audio-description` | Add an audio-description track that speaks only UI changes local OCR can see between cited frames. |
| `launch-teaser-cut` | Cut a 15 to 25 second teaser from recording stills only, rendered on the box. |
| `filler-word-cut` | Cut filler tokens listed in the local transcript and leave every other word in place. |
| `poster-frame-pick` | Choose one cited source frame as the poster image for a briefing. |
| `pace-hook-cut` | Score the opening of an accepted cut so a real spoken hook is audible inside the first three seconds. |

### Presentation — deck renderer

| Skill | Summary |
|---|---|
| `kpi-spotlight-deck` | Give each cited KPI its own big-number slide, with the action title taken from the cell label. |
| `comparison-versus-deck` | Compare two cited figures, or two cited statements, without adding a third number. |
| `risk-and-ask-deck` | Build risk and ask slides only from rows or blocks the source already labels as risks or asks. |
| `roadmap-timeline-deck` | Turn dated items already in a document or sheet into ordered step slides. |
| `decision-memo-deck` | Present the decision, the options the memo lists, and the chosen line, each cited. |
| `stakeholder-variant-deck` | Cut a shorter deck for an audience the source already names, using the same citations. |
| `one-pager-summary-deck` | Produce a one-page brief and at most six slides whose sentences are copied from the source. |
| `training-quiz-deck` | Turn questions and answers that already exist in a training doc or recording into step slides. |
| `appendix-citation-pack` | List every claim in a parent briefing as a statement slide whose body is the claim and whose footer is the citation. |
| `number-lock-refresh` | Re-read every cited cell or block and fail the briefing if a published number no longer matches. |
| `exec-narrative-deck` | Turn a long memo into a sparse leadership deck plus an appendix of the blocks that did not fit. |
| `launch-teaser-still-deck` | Build the stills-only slide companion to a launch teaser, one real frame per beat. |
| `speaker-notes-deck` | Keep the canvas to one cited idea and move delivery coaching into speaker notes. |

### Capture — ingest

| Skill | Summary |
|---|---|
| `screen-capture-ingest` | Accept a local screen recording, hash it, and store it on company MinIO with geometry and duration. |
| `mic-av-sync-align` | Measure the offset between the mic track and the capture audio locally, then shift one track. |
| `click-region-index` | Index click coordinates and times from a local input log against the capture frame size. |
| `ui-label-ocr-read` | Read on-screen text with local OCR and drop any label the detector cannot ground. |
| `window-focus-segment` | Split a capture into segments where the focused window title actually changes. |
| `redaction-mask-pass` | Mask denylisted strings found by local OCR before any later skill reads the picture. |
| `multi-monitor-stitch` | Tile recorded displays into one frame using the geometry the capture wrote down. |
| `cursor-trail-index` | Store cursor positions over time from the local capture stream or the local input log. |
| `form-fill-step-extract` | Extract one step per form field whose value local OCR sees change. |
| `error-toast-capture` | Clip the span where a toast or dialog is actually visible, with the text OCR read. |
| `before-after-snapshot-pair` | Pair two frames whose local pixel diff shows a real change, and record which is earlier. |
| `allowlisted-path-replay` | Replay a path with Playwright only against hostnames listed in the on-disk internal allowlist. |
| `clipboard-paste-detect` | Mark paste events from the local input log and describe only what local OCR sees after the paste. |
| `transcript-window-index` | Build word-timed transcript windows with local faster-whisper and store them next to the object. |

### Slideshow — cited stills

| Skill | Summary |
|---|---|
| `still-sequence-slideshow` | Auto-advance through cited frames of a recording in timeline order. |
| `chapter-still-advance` | Hold one cited frame per accepted chapter for the length of that chapter's speech. |
| `before-after-still-show` | Show the before still, then the after still, from an accepted snapshot pair. |
| `launch-still-carousel` | Play a short carousel of launch screenshots that were attached or extracted from the recording. |
| `sop-step-slideshow` | Hold one cited frame per numbered SOP step, with the step sentence as the caption. |
| `cited-frame-hold` | Hold a single cited frame for the spoken duration of its beat. |

### WBR — weekly business review

| Skill | Summary |
|---|---|
| `wbr-kpi-spine` | Lay the canonical weekly business review order from a workbook: headline, target, movers, risks, asks. |
| `wbr-executive` | Cut a short executive WBR: headline, target, top movers, one risk, one ask. |
| `wbr-ops-deep-dive` | Give each named KPI section in the workbook its own cited slide, for operators who need the full pack. |
| `wbr-region-roll-up` | One slide per region column the workbook already contains. |
| `wbr-exception-only` | Show only rows the sheet flags as exceptions, and say so when the flag column is clean. |
| `wbr-prior-week-delta` | Show movers against the previous workbook only, with both cells cited. |
| `wbr-ask-pack` | One ask slide per row on the ask sheet, with the owner only when that cell is filled. |
| `wbr-commentary-lock` | Allow narrative sentences only from commentary cells, and numbers only from numeric cells. |

### Crafts

Shared modules live under `skills/_crafts/`. New or rewritten for this expansion: `edl-cut`, `caption-track`, `frame-still`, `local-ocr`, `av-sync`, `citation-footer`, `redaction-mask`, `wbr-spine`, `slideshow-advance`, `duck-mix`, `screen-ingest`. Existing crafts keep their jobs and now declare `offline: true`.

Expansion count: **55** skills.
