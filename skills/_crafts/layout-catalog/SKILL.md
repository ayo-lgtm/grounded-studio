# craft: layout-catalog
version: 1.0.0
offline: true
source: bolt-slides component list, filtered to what house.py can draw
used_by: slide-grammar

job: Map a content shape onto a locked layout id.

rules:
  - house.py masters are cover, big-number, versus-target, movers, risk, ask, statement, and step.
  - Catalog names Cover, StatGrid, BigNumber, Comparison, Table, Steps, and Quote map onto those masters. Do not emit a master the renderer does not draw.
  - BrowserFrame and Split need a real still or table snapshot. If the master cannot hold an image, keep the sentence and store the still as a cited file.
  - Disallowed: Chat, Globe, Team, Pricing, Tabs, Accordion, CodeWindow, generated charts.
  - If a layout needs a picture and none exists, use text.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - inventing a timeline, map, or bento master inside a skill
