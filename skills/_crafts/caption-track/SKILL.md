# craft: caption-track
version: 1.0.0
offline: true
source: WebVTT from a local word transcript
used_by: caption-burn-in, filler-word-cut, sop-step-slideshow, still-sequence-slideshow

job: Build cues whose text is the spoken words and whose times are the word times.

rules:
  - At most two lines and 42 characters per line. Break on punctuation the transcript already has.
  - Do not paraphrase. Glossary may fix a spelling of a recognized word.
  - Burn with the house.py caption bar or ffmpeg using those tokens.
  - Cue drift against word times beyond 200ms fails QA.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud caption APIs
  - adding words
