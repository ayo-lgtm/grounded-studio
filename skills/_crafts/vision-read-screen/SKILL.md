# craft: vision-read-screen
version: 1.0.0
offline: true
source: Anionex agent-vision toolkit, worker-local
used_by: product-walkthrough, accessibility-audio-description, before-after-snapshot-pair, click-region-index, click-zoom-edit, form-fill-step-extract, ui-label-ocr-read

job: Read a local frame: glance, ground, detect, crop, OCR, pixel diff.

rules:
  - Tools: glance, ground, detect, crop, long_ocr, pixel_diff. They run on local files.
  - If glance names a control detect cannot find, drop it.
  - OCR engine is local Tesseract or the worker vision binary. No cloud vision fallback.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud vision APIs
  - keeping an ungrounded label
