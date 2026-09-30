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
