# craft: frame-still
version: 1.0.0
offline: true
source: local ffmpeg single-frame extract
used_by: before-after-snapshot-pair, before-after-still-show, chapter-still-advance, cited-frame-hold, error-toast-capture, launch-still-carousel, launch-teaser-cut, launch-teaser-still-deck, poster-frame-pick, side-by-side-before-after, sop-step-slideshow, still-sequence-slideshow, ui-label-ocr-read

job: Pull one PNG from a cited timestamp.

rules:
  - The timestamp must lie inside a recording citation or be an operator time that was checked against one.
  - No model upscale. Dimensions match the source frame.
  - Store the PNG in the briefing prefix on MinIO or localhost with t_ms in metadata.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - text-to-image
  - a frame from outside the citation
