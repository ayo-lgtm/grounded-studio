# 03 — User flows

## Shared shell

1. Sign in with company SSO.
2. Land on **Library**: my briefings, shared with me, templates.
3. New briefing → pick source type → pick skill (or let router suggest) → upload → wait → review → publish internally.

Permissions: draft is private to owner + explicit editors. Publish makes it visible to a workspace group.

---

## Flow A — Product walkthrough (primary v1)

**Actor:** product owner who already knows the tool.

1. Clicks **New → Walkthrough**.
2. Records in-browser (Screen Capture API) or uploads an existing Loom/OBS file. Talks naturally.
3. Optionally attaches help-center export or README.
4. System transcribes, detects cuts, proposes chapters.
5. Skill writes a cleaned script aligned to timestamps.
6. Review screen:
   - left: video
   - center: script beats
   - right: citation (`recording t=00:41–00:58`)
   - user can rewrite a sentence; validator re-checks
7. User picks voice: original cleaned audio **or** local TTS.
8. Render. Player link is internal-only.
9. Viewer asks “where do I invite a teammate?” Chat cites the transcript and seeks the video.

**Refresh:** owner uploads a 90-second clip of the changed settings page. Template keeps other chapters. Only dirty chapters re-render.

---

## Flow B — Word / announcement / leadership briefing

**Actor:** lead who already wrote the document.

1. **New → Briefing from document**.
2. Upload docx/pdf/md.
3. Pick tone skill: `leadership-brief` | `launch-announcement` | `training-explainer`.
4. Compiler extracts outline, proposes 6–12 slides. Each slide maps to paragraph ids.
5. Review: edit titles, kill a slide, pin a quote.
6. Optional narration (local TTS) + optional second language.
7. Outputs: HTML deck + optional 3-minute voiced version that shows the slides, not invented B-roll.

Leadership visual grammar (enforced by skill): one idea per slide, large number if present in source, no decorative stock photos unless they exist in the upload.

---

## Flow C — Weekly Excel pack

**Actor:** manager with a stable template.

1. First week: upload workbook + pick `weekly-ops-review`.
2. User marks **story cells** (or the skill guesses from header names: Revenue, NRR, Churn, Open risks).
3. Compiler builds beats: headline → vs target → movers → risks → ask.
4. Every number in the script has `sheet!cell`.
5. Slides embed a snapshot of the actual range, not a regenerated chart from memory.
6. Save as template “Monday exec pack”.
7. Next Monday: upload new file. Diff view. Confirm. Re-render dirty slides only.

If a cell is empty or a header disappeared, the job stops that beat and flags it. It does not invent last week’s number.

---

## Flow D — Localized sibling

1. Open a published briefing.
2. **Create language** → `es-419` / `fr-FR` / approved list.
3. Translator LLM (local) translates script only. Citations stay.
4. Numeric tokens are locked (do not translate `12.4%` into a new value).
5. New TTS track. Same video pictures or same slides.
6. Chat in that language still retrieves original chunks plus translated script.

---

## Flow E — Grounded chat

1. Viewer opens player.
2. Asks a question.
3. Retriever searches only this briefing’s index.
4. If hit: answer + citations + “jump”.
5. If miss: “Not in this briefing. Ask the owner or attach a doc.”

No web search. No general world knowledge.

---

## Error flows

| Event | UX |
|---|---|
| Citation QA fail | Show failing lines, do not render |
| Unsupported codec | Ask for mp4/h264 re-export |
| Spreadsheet with macros | Strip macros, warn, parse values only |
| File labeled restricted | Only restricted-cleared workspace can open |
| Job > SLA | Email/Slack *internal* webhook, keep partial script |
