# craft: wbr-spine
version: 1.0.0
offline: true
source: weekly-ops-review beat order
used_by: wbr-ask-pack, wbr-commentary-lock, wbr-exception-only, wbr-executive, wbr-kpi-spine, wbr-ops-deep-dive, wbr-prior-week-delta, wbr-region-roll-up

job: Shared order for WBR skills: cover, headline, versus target, movers, risks, asks.

rules:
  - Omit a beat the sheet cannot cite. Empty required KPIs fail closed.
  - Do not interpolate weeks or reuse last week's empty cell.
  - Layouts stay inside cover, big-number, versus-target, movers, risk, and ask.
  - weekly-ops-review remains the generic template. These skills specialize it.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a chart
  - a recommendation that is not a text cell
