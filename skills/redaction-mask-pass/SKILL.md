# skill: redaction-mask-pass
version: 1.0.0
offline: true
area: capture
job: Mask denylisted strings found by local OCR before any later skill reads the picture.

inputs_required:
  - recording or still
  - workspace denylist of patterns such as email or account-id shapes
inputs_optional:
  - operator rectangles already marked on the frame

truth_source: OCR hits that match the denylist, plus operator rectangles

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Run ui-label-ocr-read locally.
  - A box is masked when its text matches the denylist or an operator marked it.
  - Burn an opaque rectangle with local ffmpeg drawbox. The mask is flat and has no replacement text.
  - Write redaction.json with times and boxes. Do not write the matched secret into the log; write the pattern id only.
  - Replace the working object. Keep the unredacted original in a restricted prefix if policy says so; later skills receive only the redacted key.

visual_grammar:
  - the mask hides pixels; it does not redraw the screen or use house slide chrome
  - no blur strong enough to be reversed is required; the rectangle is opaque

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - sending frames to a cloud DLP API
  - replacing a secret with a realistic fake value
  - continuing the pipeline on the unredacted object after a hit

qa_checks:
  - a second local OCR pass on the output finds no denylist match
  - the log contains pattern ids, not the matched text
  - later manifest points at the redacted key
  - offline is true

outputs:
  - redacted recording
  - redaction.json

refresh_policy: re-run when the denylist or the source changes; fail closed if the second pass still matches

crafts:
  - redaction-mask
  - local-ocr
