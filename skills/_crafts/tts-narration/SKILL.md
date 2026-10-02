# craft: tts-narration
version: 1.0.0
offline: true
source: Piper or Kokoro on the worker; weights preloaded
used_by: leadership-brief, launch-announcement, weekly-ops-review, localize, accessibility-audio-description, exec-narrative-deck, local-tts-duck-overlay

job: Speak an accepted beat verbatim with the workspace-pinned local voice.

rules:
  - Prefer original walkthrough audio when it is usable.
  - One wav per beat so refresh can replace a single line.
  - Glossary pronunciation map may bias a word already in the beat. It may not add words.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - ElevenLabs, HeyGen, cloud TTS, reading text that failed citation QA
