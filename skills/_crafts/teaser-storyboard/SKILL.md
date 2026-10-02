# craft: teaser-storyboard
version: 1.0.0
offline: true
source: latent-spaces/brag rubric and tones, stills from the recording, rendered locally
used_by: launch-teaser, launch-still-carousel, launch-teaser-cut, launch-teaser-still-deck

job: Plan a 15–25s stills-only teaser before any render.

rules:
  - Hook in the first 2–3 seconds. Total duration 15–25 seconds.
  - Tones change hold length only: default, polished, deadpan, cinematic, app-store.
  - Every still is a recording frame or an attached screenshot. On-screen copy is OCR or a cited sentence.
  - Render with local Remotion or on-box Hyperframes. If the binary is missing, fail closed.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - codebase-only invented screens
  - cloud render
  - Veo, Runway, HeyGen
