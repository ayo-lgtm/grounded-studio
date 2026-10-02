# skill: error-toast-capture
version: 1.0.0
offline: true
area: capture
job: Clip the span where a toast or dialog is actually visible, with the text OCR read.

inputs_required:
  - recording
  - local OCR samples
inputs_optional:
  - a list of known toast containers from prior OCR, still re-checked on this file

truth_source: frames where the toast text is visible

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Find OCR strings that appear and then disappear, sitting in a small region typical of a toast or dialog. The region must be detected, not assumed from a template that is not in the frame.
  - Clip from the first frame the text is present to the last, plus 200ms of handle on each side if those frames exist.
  - The beat text is the OCR string. Do not explain the error.
  - If no toast is found, output an empty list and succeed. Do not invent an error.

visual_grammar:
  - optional mp4 is the clipped span via local ffmpeg
  - layout, if a script beat is emitted: step

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - staging an error that was not on screen
  - cloud log correlation
  - paraphrasing the toast

qa_checks:
  - every clip's text is an OCR substring at the start frame
  - the text is absent in a sample before t_start and after t_end, within the handle
  - offline is true

outputs:
  - toasts.json
  - optional clip mp4 per toast

refresh_policy: rebuild when the recording changes; an empty result stays empty

crafts:
  - local-ocr
  - frame-still
  - edl-cut
