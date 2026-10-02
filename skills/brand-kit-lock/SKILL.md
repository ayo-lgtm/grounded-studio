# skill: brand-kit-lock
version: 1.0.0
offline: true
area: deck
job: Lock palette and type to house.py. Do not fetch a brand service.

inputs_required:
  - a workbook or a document that already compiles
inputs_optional:
  - no logo file; house chrome has no third-party mark

truth_source: house.py tokens and the cited source

story_beats:
  - Read paper, ink, muted, rule, accent, negative, and theater from house.py.
  - Title and UI fonts are the house stacks. A script must not carry font, color, css, theme, or background.
  - A logo is absent unless a local asset is already in the workspace. This skill does not download one.
  - The deck still cites cells or blocks. Brand lock does not add a claim.
  - Empty required KPIs still fail closed.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - layouts from the underlying workbook or document skill

qa_checks:
  - offline is true
  - brand.source is house.py
  - no style key on a beat
  - numbers still match cited cells

outputs:
  - deck html
  - script.brand

refresh_policy: house.py is the only brand input

crafts:
  - brand-kit
  - slide-grammar

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
