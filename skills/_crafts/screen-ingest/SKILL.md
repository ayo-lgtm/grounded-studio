# craft: screen-ingest
version: 1.0.0
offline: true
source: ffprobe plus company MinIO
used_by: allowlisted-path-replay, clipboard-paste-detect, cursor-trail-index, mic-av-sync-align, multi-monitor-stitch, screen-capture-ingest

job: Hash a local media file and store it with duration and geometry.

rules:
  - sha256, byte length, width, height, fps, duration_ms, and audio presence go in manifest.json.
  - The bucket is localhost or company MinIO. No public pre-signed upload.
  - A new upload uses a new key when an accepted briefing already points at the old one.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud ingest
  - public egress of the bytes
