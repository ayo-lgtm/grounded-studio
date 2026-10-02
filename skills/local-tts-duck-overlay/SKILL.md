# skill: local-tts-duck-overlay
version: 1.0.0
offline: true
area: video
job: Lay a local Piper or Kokoro reading of an accepted script line under a ducked source bed.

inputs_required:
  - accepted script whose beat text is already citation-checked
  - source recording or cut on localhost or company MinIO
  - workspace-pinned local voice for Piper or Kokoro
inputs_optional:
  - glossary pronunciation map stored in the workspace

truth_source: accepted beat text; TTS may not add or drop words

story_beats:
  - If the beat already keeps usable original speech, skip TTS for that beat and say so in the EDL.
  - Synthesize one wav per beat on the worker. Text is the beat text verbatim.
  - Duck the source bed by 12 dB while the wav plays, using ffmpeg volume automation. Restore the bed after.
  - Align the wav to the beat's output time. Do not cover a different beat.
  - Write mix.json with voice id, beat id, and file hash. One file per beat so refresh can replace one line.

visual_grammar:
  - renderer: recording editor
  - layout: unchanged from the parent beat
  - picture is untouched
  - no on-screen lyrics or waveform

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - ElevenLabs or any cloud voice
  - reading text that is not the accepted beat
  - music beds, stingers, or a second voice
  - generating speech for a beat that failed citation QA

qa_checks:
  - wav transcript from a second local ASR pass matches beat text, or the beat stays in review
  - duck automation exists only where a wav exists
  - voice id is the workspace pin
  - no network socket to a TTS host
  - offline is true

outputs:
  - per-beat wav
  - mixed mp4
  - mix.json

refresh_policy: replace the wav and the duck span for a dirty beat; leave other beats

crafts:
  - tts-narration
  - duck-mix
  - video-edit
