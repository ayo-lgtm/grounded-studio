# craft: edl-cut
version: 1.0.0
offline: true
source: local ffmpeg concat and the recording editor
used_by: chapter-card-overlay, chaptered-demo-cut, click-zoom-edit, dead-air-trim, error-toast-capture, filler-word-cut, highlight-reel-from-chapters, multi-clip-concat, multi-monitor-stitch, pace-hook-cut

job: Represent every cut as edl.json and render only those spans.

rules:
  - Each row has clip id, source object, t_in_ms, t_out_ms, and a reason.
  - Use the concat demuxer. Re-encode a span only when the cut is not on a keyframe.
  - Do not synthesize frames between rows.
  - Store a map from output time back to source time.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - generated transitions
  - cloud transcode
