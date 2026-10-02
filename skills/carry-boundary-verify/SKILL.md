# skill: carry-boundary-verify
version: 1.0.0
offline: true
area: video
job: Check a cut for carry-boundary continuity and fail closed when a beat replaces the picture.

inputs_required:
  - an accepted recording script, or a recording plus a local transcript
inputs_optional:
  - the rendered mp4, probed locally

truth_source: the edit's continuity record and the source timestamps

story_beats:
  - Read edit.continuity before watching the film.
  - Every pair of neighboring cuts needs a boundary with a survivor.
  - Survivor is a screen label that continues, or the outgoing frame.
  - Reject a boundary whose kind is replace, and reject a missing boundary.
  - This check does not render a new picture and does not call a model.
  - Probe notes stay in the job error. They are not a second edit.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - no new pixels

qa_checks:
  - offline is true
  - continuity mode is carry-boundary
  - survivor is present on every boundary
  - no slideshow replace

outputs:
  - pass or a compile error that names the boundary

refresh_policy: re-check after any edit that changes cuts

crafts:
  - carry-boundary

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
