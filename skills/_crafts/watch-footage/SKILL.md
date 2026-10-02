# craft: watch-footage
version: 1.0.0
offline: true
source: diffusionstudio watch pattern, local files only
used_by: product-walkthrough, sop-training, grounded-qa, chaptered-demo-cut, highlight-reel-from-chapters, pace-hook-cut, transcript-window-index, window-focus-segment

job: Answer what happens, where it happens, and which words were said, with timestamps.

rules:
  - Prefer transcript timestamps from local faster-whisper.
  - Sample frames at cuts and run vision-read-screen when the answer is visual.
  - Always return t_start_ms and t_end_ms.
  - A miss refuses. It does not guess.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - web search
  - describing UI that was not on screen
