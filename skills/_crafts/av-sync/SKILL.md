# craft: av-sync
version: 1.0.0
offline: true
source: local waveform alignment
used_by: mic-av-sync-align

job: Measure offset_ms between two local audio files and shift without stretching.

rules:
  - Cross-correlate or align a clap. Record the method.
  - Absolute offset above 500ms waits for a person.
  - Keep the original objects. Write a new hashed object.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud alignment APIs
  - time-stretching speech
