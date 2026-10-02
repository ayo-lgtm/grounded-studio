# skill: offline-quality-gate
version: 1.0.0
offline: true
area: review
job: Pass, warn, or fail a briefing before a share link is issued.

inputs_required:
  - a compiled script
inputs_optional:
  - voiceover or mixed mp4 for a loudness probe

truth_source: the script citations, the workbook cells, and local ffmpeg measurements

story_beats:
  - Run citation QA first. A beat with no citation fails.
  - Empty required KPI cells fail. Do not estimate them.
  - Carry-boundary scripts fail when a survivor is missing.
  - Clipped audio, max volume hotter than -1 dB, fails.
  - Uniform cadence and a take with no rest are warnings, not a silent pass.
  - The gate writes quality.json. It does not send the briefing anywhere.

visual_grammar:
  - renderer: whichever the source skill used
  - no new layout

qa_checks:
  - offline is true
  - status is pass, warn, or fail
  - fail stops the share
  - no public probe endpoint

outputs:
  - quality.json

refresh_policy: re-run after compile or a new mix

crafts:
  - quality-gate

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
