# craft: local-ocr
version: 1.0.0
offline: true
source: Tesseract or worker vision tools on local frames
used_by: accessibility-audio-description, click-region-index, clipboard-paste-detect, error-toast-capture, form-fill-step-extract, redaction-mask-pass, ui-label-ocr-read, window-focus-segment

job: Return text and boxes for pixels that a local detector can ground.

rules:
  - Sample with ffmpeg. Recognize on the worker.
  - Drop a string with no box. Log the drop.
  - Do not translate.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud OCR
  - keeping glance-only labels
