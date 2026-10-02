# skill: cursor-trail-index
version: 1.0.0
offline: true
area: capture
job: Store cursor positions over time from the local capture stream or the local input log.

inputs_required:
  - pointer-move log captured with the session, or frames where the cursor is part of the recording
inputs_optional:
  - click index to mark downs

truth_source: the log or the recorded cursor pixels

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Sample at least every 100ms. Store t_ms, x, y.
  - If the only source is pixels, detect the cursor locally. If detection fails, omit those samples. Do not invent a path.
  - Do not draw the trail onto the briefing video in this skill. The index is for later zoom and QA.
  - Clip coordinates to the frame.

visual_grammar:
  - no render required
  - a debug PNG sequence is allowed locally and is not a briefing artifact unless a person attaches it

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - synthesizing a smooth path through missing samples
  - cloud cursor analytics

qa_checks:
  - samples are time-ordered
  - coordinates lie inside the frame
  - gaps are recorded rather than interpolated
  - offline is true

outputs:
  - cursor.json

refresh_policy: rebuild when the log or the recording changes

crafts:
  - screen-ingest
