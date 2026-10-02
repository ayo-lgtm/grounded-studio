# skill: placement-formats-export
version: 1.0.0
offline: true
area: video
job: Derive 16:9, 9:16, and 1:1 placements from a master with a safe zone, using local ffmpeg.

inputs_required:
  - a master picture on disk, or a compiled deck or recording
inputs_optional:
  - a safe-zone fraction, default 0.9

truth_source: the master pixels

story_beats:
  - The master is 16:9. Variants contain the same pixels inside the safe zone.
  - Scale down to fit, then pad. Pad color is the house theater token.
  - Do not crop away a cited control to fill a vertical frame.
  - Do not generate a new background plate.
  - Write the ffmpeg filter for each ratio into placement.json.
  - Render a variant only with local ffmpeg when an operator asks for that file.

visual_grammar:
  - renderer: deck or recording, unchanged
  - placements are filters, not new layouts
  - ratios: 16:9, 9:16, 1:1

qa_checks:
  - offline is true
  - every variant names width, height, and a local vf
  - safe zone is inside the frame
  - pad color is the house theater token

outputs:
  - placement.json
  - optional variant mp4 from local ffmpeg

refresh_policy: rebuild variants when the master file changes

crafts:
  - placement-formats

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
