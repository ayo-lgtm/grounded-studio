# craft: citation-footer
version: 1.0.0
offline: true
source: house.py footer line
used_by: appendix-citation-pack, comparison-versus-deck, decision-memo-deck, exec-narrative-deck, kpi-spotlight-deck, number-lock-refresh, one-pager-summary-deck, risk-and-ask-deck, roadmap-timeline-deck, training-quiz-deck, wbr-commentary-lock, wbr-exception-only, wbr-kpi-spine, wbr-ops-deep-dive, wbr-prior-week-delta, wbr-region-roll-up

job: Put the citation in the footer and nowhere else as decoration.

rules:
  - Recording cites t_start_ms–t_end_ms. Workbook cites sheet!addr. Document cites block_id.
  - The skill passes the string. house.py draws the footer.
  - A slide with no citation does not render.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a footer slogan
  - hiding the address to make the slide cleaner
