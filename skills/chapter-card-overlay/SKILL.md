# skill: chapter-card-overlay
version: 1.0.0
offline: true
area: video
job: Insert a short title card before each chapter using the label read off the capture.

inputs_required:
  - accepted chapter list with recording citations
  - local OCR or transcript string for each chapter title
inputs_optional:
  - the cut mp4 this card sequence should preface

truth_source: chapter title strings already accepted on the briefing; the card does not write a new title

story_beats:
  - One card per chapter, in chapter order.
  - Card text is the chapter title verbatim. If it is longer than 42 characters, fail that card instead of rewriting it.
  - Card duration is 1.5s. It does not consume source picture. The following span still cites the original recording times.
  - Paint the card with the recording editor's house.py card (paper, ink, Georgia). This skill passes the string only.
  - Concat card then source span with local ffmpeg. Write both pieces into the EDL with kind card or source.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - chrome comes from house.py
  - no logo, date, or episode number unless that string is the chapter title

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - composing a smarter title than the accepted chapter name
  - stock backgrounds, generated textures, or a screenshot that is not the cited frame
  - putting body copy on the card

qa_checks:
  - card count equals chapter count
  - card text equals the chapter title byte for byte
  - card beats cite the same recording span as the chapter they introduce
  - local still of each card shows the full title inside the frame
  - offline is true and no font was fetched from the network

outputs:
  - edl.json
  - mp4
  - script json

refresh_policy: rebuild a card when its chapter title changes; leave other cards

crafts:
  - video-edit
  - edl-cut
