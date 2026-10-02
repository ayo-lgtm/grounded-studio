# craft: duck-mix
version: 1.0.0
offline: true
source: local ffmpeg volume automation
used_by: local-tts-duck-overlay

job: Lower the source bed under a local TTS wav and restore it after.

rules:
  - Default duck is 12 dB for the wav's duration only.
  - Skip TTS when the original speech is kept.
  - One wav per beat.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - music beds
  - cloud mix services
  - ducking a beat that has no wav
