# craft: video-edit
version: 1.0.0
offline: true
source: OpenMontage ffmpeg pattern, source-faithful, local binary only
used_by: product-walkthrough, sop-training, feature-delta, caption-burn-in, chapter-card-overlay, chaptered-demo-cut, click-zoom-edit, dead-air-trim, filler-word-cut, highlight-reel-from-chapters, local-tts-duck-overlay, multi-clip-concat, pace-hook-cut, side-by-side-before-after

job: Cut, zoom, caption, duck, scale, and concat real footage with an EDL beside the file.

rules:
  - Allowed picture operations: drop measured dead air, cut listed filler tokens, chapter cards from source labels, crop-zoom on a logged click, burn spoken captions, duck under local TTS, 1080p scale of source pixels, concat kept spans.
  - Keep edl.json next to the mp4 so a refresh can diff spans.
  - ffmpeg runs on the worker. No cloud transcode.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - text-to-video B-roll, avatars, generated UI, cloud music
