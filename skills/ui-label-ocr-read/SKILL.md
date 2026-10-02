# skill: ui-label-ocr-read
version: 1.0.0
offline: true
area: capture
job: Read on-screen text with local OCR and drop any label the detector cannot ground.

inputs_required:
  - recording or still on localhost or company MinIO
inputs_optional:
  - sample times; default is cuts plus one frame per second

truth_source: pixels in the frame

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Sample frames with local ffmpeg.
  - Run local Tesseract or the worker vision tools glance and long_ocr. Tools run on local files.
  - Keep a label only when detect or ground returns a box for that string.
  - If glance names a control detect cannot find, drop it.
  - Write labels.json with text, box, t_ms, and engine name. No cloud vision fallback.

visual_grammar:
  - no script text is authored here
  - boxes are pixel rectangles on the source frame

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud OCR
  - translating a label
  - keeping a low-confidence string the grounder rejected

qa_checks:
  - every kept label has a box inside the frame
  - engine name is a local binary
  - dropped glance-only strings are listed in the reject log
  - offline is true

outputs:
  - labels.json
  - sampled frames
  - reject-log.json

refresh_policy: re-read when the recording object changes

crafts:
  - local-ocr
  - vision-read-screen
  - frame-still
