# skill: window-focus-segment
version: 1.0.0
offline: true
area: capture
job: Split a capture into segments where the focused window title actually changes.

inputs_required:
  - recording
  - local window-title log captured with the session, or OCR of the title bar at sample times
inputs_optional:
  - click index

truth_source: title strings from the log or from OCR of the title bar

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Read title changes in order. A segment starts when the title string changes and ends at the next change.
  - Title text is copied. Do not map it to a product area the string does not name.
  - Ignore flicker shorter than 300ms by merging back into the previous title, and record the merge.
  - Each segment is a recording citation. Later chapter skills may use these segments. They are not chapters until a chapter skill accepts them.

visual_grammar:
  - no render
  - segment list is data

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - splitting on a guessed task when the title did not change
  - cloud window-tracking agents

qa_checks:
  - segments cover the duration without overlap
  - each title equals a log line or an OCR string at the start time
  - offline is true

outputs:
  - segments.json

refresh_policy: rebuild when the log or the OCR sample changes

crafts:
  - local-ocr
  - watch-footage
