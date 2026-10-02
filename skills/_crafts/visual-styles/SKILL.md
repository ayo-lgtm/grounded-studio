# craft: visual-styles
version: 1.0.0
offline: true
source: distilled from SlideSpeak presentation-design prompts; tokens stay in house.py
used_by: slide-grammar, kpi-spotlight-deck

job: Pick a style family so the renderer can choose density. Do not pick colors.

rules:
  - Families: boardroom, consulting, pitch, teaching, product-light, product-dark, report.
  - boardroom: leadership, QBR, weekly ops. consulting: action title plus evidence. pitch: launch. teaching: SOP. report: numeric packs.
  - Infer from skill id unless the workspace brand overrides.
  - The family never sets hex, type, or spacing. house.py does.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - novelty themes
  - claiming a trademarked firm style in the output
  - passing color or CSS on a beat
