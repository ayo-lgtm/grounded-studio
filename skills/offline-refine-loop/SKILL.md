# skill: offline-refine-loop
version: 1.0.0
offline: true
area: review
job: Turn a quality-gate finding into the cheapest local fix.

inputs_required:
  - a quality report
inputs_optional:
  - the script the report scored

truth_source: the gate findings

story_beats:
  - A missing survivor asks for a carry hold of the outgoing frame.
  - A missing citation asks for a recaption from the local transcript.
  - An empty KPI fails closed. Do not invent a number to clear the gate.
  - Uniform cadence or no rest asks for a trim, not a generated shot.
  - Clipped or loud audio asks for a duck and a limiter, local ffmpeg only.
  - Each action records fix, why, and where. Where is always local.
  - Stop when the gate is not fail. Do not loop into a cloud render.

visual_grammar:
  - renderer: unchanged
  - the loop does not add a layout

qa_checks:
  - offline is true
  - every action is local
  - empty numbers are fail-closed
  - no action names a hosted model

outputs:
  - script.refine list
  - quality.json

refresh_policy: one local fix, then the gate again

crafts:
  - refine-loop
  - quality-gate

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
