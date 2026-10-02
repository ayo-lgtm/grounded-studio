# skill: click-region-index
version: 1.0.0
offline: true
area: capture
job: Index click coordinates and times from a local input log against the capture frame size.

inputs_required:
  - recording manifest
  - local input log of pointer downs captured with the session
inputs_optional:
  - hit rectangles from local OCR

truth_source: the input log and the frame geometry in the manifest

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Normalize log times onto the capture clock using the session start both files share.
  - Drop events outside the frame or outside the duration.
  - Store x, y, t_ms, frame_w, frame_h. Do not store a control name unless local OCR grounds one at that point.
  - If the log is missing, fail. Do not infer clicks from cursor motion alone in this skill.

visual_grammar:
  - no zoom is rendered here; click-zoom-edit consumes the index
  - optional debug overlay is a local PNG with a marker at the logged point, not a new UI

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - inventing a click on a likely button
  - reading clicks from a cloud session replay product

qa_checks:
  - every point lies inside the frame
  - t_ms is inside the duration
  - index rows cite the recording
  - offline is true

outputs:
  - clicks.json

refresh_policy: rebuild when the log or the manifest geometry changes

crafts:
  - vision-read-screen
  - local-ocr
