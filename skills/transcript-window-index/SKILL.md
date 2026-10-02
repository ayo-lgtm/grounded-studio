# skill: transcript-window-index
version: 1.0.0
offline: true
area: capture
job: Build word-timed transcript windows with local faster-whisper and store them next to the object.

inputs_required:
  - recording with an audio stream on localhost or company MinIO
inputs_optional:
  - workspace glossary to bias spellings that are already in the audio
  - language hint from the workspace allowlist

truth_source: the audio in the recording

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Run faster-whisper on the worker. Weights are preloaded. There is no cloud ASR fallback.
  - Emit words with t_start_ms and t_end_ms, plus segments of roughly 10 to 30 seconds for retrieval.
  - Do not punctuate in a way that adds words. Punctuation may be inserted; tokens stay the recognized words.
  - Store transcript.json beside the object. Citations later point at these times.
  - If the audio stream is missing, fail. Do not describe the video instead.

visual_grammar:
  - no video render
  - windows are data for watch-footage and the recording editor

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud ASR
  - summarizing the transcript in this skill
  - translating

qa_checks:
  - every word has timestamps inside the duration
  - word order matches the audio order
  - engine recorded in the file is faster-whisper or another local binary named in the manifest
  - offline is true

outputs:
  - transcript.json
  - words.json

refresh_policy: re-transcribe when the audio object or the model id changes; keep the old file until the new one passes QA

crafts:
  - watch-footage
