# skill: launch-teaser-cut
version: 1.0.0
offline: true
area: video
job: Cut a 15 to 25 second teaser from recording stills only, rendered on the box.

inputs_required:
  - recording on localhost or company MinIO, or attached screenshots that are real captures
  - local still extractor
inputs_optional:
  - launch document for a hook sentence that already exists in a cited block
  - tone: default, polished, deadpan, cinematic, or app-store; tone changes timing, not pixels

truth_source: recording frames or attached screenshots; on-screen words come from OCR or the transcript

story_beats:
  - Outline the teaser before render: hook, one change, one proof frame, one closer. Four beats maximum.
  - Hook lands in the first 2 to 3 seconds and uses a real frame. The hook sentence must be spoken in that span or copied from a cited doc block.
  - Every still is extracted with local ffmpeg at a cited timestamp, or is an attached image already in the briefing.
  - Total duration is 15 to 25 seconds. If the outline cannot fill 15 seconds without inventing a beat, fail.
  - Render with local Remotion in the worker checkout or self-hosted Hyperframes on the box. If neither binary is present, fail closed. Do not call a render API.
  - On-screen copy is OCR text or the cited sentence. Show the real UI. Do not redraw it.

visual_grammar:
  - renderer: local Remotion or on-box Hyperframes, stills only
  - layout: step
  - type and color, if a card is needed, come from house.py tokens
  - no motion that is not a cut or a crop-zoom toward a cited click
  - tones from the teaser-storyboard craft affect hold length only

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - Veo, Runway, HeyGen, or any text-to-video model
  - codebase-only screens that were never recorded
  - cloud Remotion SaaS
  - music from a library that is not already a local file attached by the user; default is silence
  - invented UI, prices, or dates

qa_checks:
  - duration is between 15000 and 25000 ms
  - first picture change is at or before 3000 ms
  - every still's timestamp or attachment id resolves
  - every on-screen string is a substring of OCR or a cited block
  - render log shows a local binary and no public host
  - offline is true

outputs:
  - teaser mp4
  - storyboard.json with still citations
  - script json

refresh_policy: rebuild when a cited frame or the hook block changes; do not keep a still whose timestamp no longer exists

crafts:
  - teaser-storyboard
  - frame-still
