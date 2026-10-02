# skill: clipboard-paste-detect
version: 1.0.0
offline: true
area: capture
job: Mark paste events from the local input log and describe only what local OCR sees after the paste.

inputs_required:
  - input log that records paste shortcuts or paste events with timestamps
  - recording
inputs_optional:
  - OCR samples after each event

truth_source: the input log event and the frame after it

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - A paste is a log event, not a guess from a sudden text change.
  - Do not read the operating-system clipboard of the build machine, and do not copy clipboard contents off the box.
  - After the event, OCR the focused field. The step text is that OCR string, unless redaction-mask-pass would hide it, in which case the step says paste and omits the text.
  - Cite the recording from the event time to the next stable OCR sample.

visual_grammar:
  - no render required
  - each event can become a step beat for a later skill

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud clipboard sync
  - logging clipboard contents into the job log when the denylist matches
  - inferring a paste without a log event

qa_checks:
  - every emitted step has a log event time
  - visible text matches OCR or is omitted under redaction
  - offline is true

outputs:
  - pastes.json

refresh_policy: rebuild when the log or the recording changes

crafts:
  - local-ocr
  - screen-ingest
