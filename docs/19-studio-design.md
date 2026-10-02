# 19 — The studio (room) design

`apps/api/app/room.html` is the whole product UI: one self-contained page,
no remote fonts, scripts, images or styles (CSP `default-src 'self'`).

## Two surfaces, two languages

* **The shell** is a warm, translucent theater: a near-black ground with a slow
  jade/amber aurora, frosted-glass panels (`backdrop-filter`), soft depth,
  rounded geometry, a serif display face and a system sans for UI.
* **The briefing** keeps the locked house style ([13](13-house-style.md)):
  paper, ink, accent and negative, Georgia titles, the eight deck masters.
  The shell frames it on a "screen" and never restyles it.

## Layout

| Region | What it holds |
|---|---|
| Header | brand, current briefing + skill/version + review state, view switch (Film · Deck · Script), Accept, re-render, copy link, New, deployment posture, signed-in user |
| Library (left) | search, briefings with state dot, skill and date; posture footer |
| Stage (centre) | intake hero and drop zone · live pipeline · the projected briefing |
| Chapters (bottom) | numbered chapter pills; film transport with scrubber |
| Evidence (right) | **Ask** — grounded chat with citation chips and explicit refusals · **Sources** — every citation of the current beat resolved to its cell value/formula, block text/page, or transcript line, plus each number's lineage (read from cell, quoted, or computed with formula and operands) · **Provenance** — skill and craft versions, contract hash, checks that passed, which provider wrote the words, where it ran |

## Flows

1. **Intake.** Pick a briefing kind (grouped: business reviews, documents,
   recordings), drop a file or `.zip`. Type is detected server-side.
2. **Pipeline.** Upload → read sources → (transcribe) → write & verify → render,
   each step with live state and elapsed time. Failures show the exact
   grounding reasons and never a half-made briefing.
3. **Review.** Navigate with ← → (Space plays film), `/` focuses Ask, `N` starts
   a new briefing. Open Sources to audit any slide, then Accept.

## Accessibility and motion

Focus rings on every control, `aria-live` status, labelled icon buttons,
keyboard navigation, `prefers-reduced-motion` honoured, responsive down to
phone width (library becomes a swipeable strip, evidence stacks below).
