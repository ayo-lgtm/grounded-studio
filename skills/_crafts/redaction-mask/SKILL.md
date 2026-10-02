# craft: redaction-mask
version: 1.0.0
offline: true
source: local ffmpeg drawbox over OCR hits
used_by: redaction-mask-pass

job: Cover denylisted text with an opaque rectangle before later skills see the picture.

rules:
  - Match the workspace denylist or an operator rectangle.
  - Log the pattern id, not the matched secret.
  - Run a second OCR pass. A remaining hit fails the job.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud DLP
  - replacing a secret with a fake realistic value
