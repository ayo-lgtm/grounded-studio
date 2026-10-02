# craft: slide-grammar
version: 1.0.0
offline: true
source: adapted from stackblitz/bolt-slides and SlideSpeak slide-design-skill, locked to house.py
used_by: leadership-brief, launch-announcement, weekly-ops-review, sop-training, appendix-citation-pack, comparison-versus-deck, decision-memo-deck, exec-narrative-deck, kpi-spotlight-deck, launch-teaser-still-deck, number-lock-refresh, one-pager-summary-deck, risk-and-ask-deck, roadmap-timeline-deck, speaker-notes-deck, stakeholder-variant-deck, training-quiz-deck, wbr-ask-pack, wbr-commentary-lock, wbr-exception-only, wbr-executive, wbr-kpi-spine, wbr-ops-deep-dive, wbr-prior-week-delta, wbr-region-roll-up

job: Turn an accepted script into an HTML deck without inventing content.

rules:
  - Ground every slide in script beats and citations. No placeholders, fake names, or invented numbers.
  - Narrative outline before visuals. One idea per slide. Default length 6 to 16 slides unless the skill documents a tighter cap or an appendix exception.
  - Cover from the source title. Close on an ask only if the source contains an ask.
  - Style tokens from house.py or the workspace brand via visual-styles. Do not reskin a starter deck.
  - Center text-only slides. A table is cited cells. No generated charts and no third-party logos.
  - Speaker coaching stays in speaker_notes.md. The canvas stays readable.
  - After render, local PNG stills are checked for overflow. Clipping fails the slide.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - style, color, font, css, theme, or background keys on a beat
  - cloud slide APIs
