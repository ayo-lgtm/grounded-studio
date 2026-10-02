# skill: form-fill-step-extract
version: 1.0.0
offline: true
area: capture
job: Extract one step per form field whose value local OCR sees change.

inputs_required:
  - recording of a form
  - local OCR samples
inputs_optional:
  - click index
  - window segments

truth_source: OCR text in field boxes before and after a change

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Detect field regions locally. Track the text in each region over time.
  - A step starts when the text changes and the click index has a click in that region, or when the text changes and stays for 500ms.
  - Step sentence is the label plus the new value only if both are OCR strings. If the value matches the redaction denylist, the step says the field changed and does not repeat the value.
  - Order steps by t_ms. Do not merge two fields.

visual_grammar:
  - no video render required; the output is a step list other skills can cite
  - each step cites a recording span

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - typing a value that OCR did not read
  - reading the live DOM from a public site
  - including a denylisted value in the step text

qa_checks:
  - each step cites t_start_ms and t_end_ms
  - label and value are substrings of OCR or the value is redacted by policy
  - step times increase
  - offline is true

outputs:
  - form-steps.json
  - script fragment of step beats

refresh_policy: rebuild when OCR or the recording changes

crafts:
  - local-ocr
  - vision-read-screen
