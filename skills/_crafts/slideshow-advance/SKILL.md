# craft: slideshow-advance
version: 1.0.0
offline: true
source: local ffmpeg still concat
used_by: before-after-still-show, chapter-still-advance, cited-frame-hold, launch-still-carousel, sop-step-slideshow, still-sequence-slideshow

job: Hold cited frames in order for the spoken duration.

rules:
  - One still per beat. Extract locally.
  - Hold equals the spoken span, or 2500ms when the frame has no speech, and the EDL says which.
  - Hard cuts only. A crop must stay inside the frame and on a cited click.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - dissolves that blend two UI states
  - stock motion
  - cloud render
