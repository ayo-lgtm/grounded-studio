# skill: side-by-side-before-after
version: 1.0.0
offline: true
area: video
job: Show two cited captures in one frame, before on the left and after on the right, using only their pixels.

inputs_required:
  - before recording or still, with a recording citation
  - after recording or still, with a recording citation
  - pair manifest that states which object is before and which is after
inputs_optional:
  - local OCR labels for each side

truth_source: the two source objects and the pair manifest

story_beats:
  - Refuse the job if either object is missing or the manifest disagrees with the citations.
  - Scale each side to the same height with local ffmpeg. Pad with black only to equalize height. Do not paint UI into the pad.
  - hstack the two rasters. Left is before. Right is after. The manifest is the only authority for that assignment.
  - A label is allowed only when it is the OCR string or the timestamps. Do not write the words improved or fixed.
  - Duration is the shorter input if both are video, and the job records that choice. Do not loop the shorter side.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - composition is a spatial join of two sources, not a generated comparison graphic
  - no house slide chrome inside the video frame except a later caption-burn-in

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - morphing, generative interpolation, or a slider animation that invents intermediate UI
  - swapping sides to make the story clearer
  - adding a third panel

qa_checks:
  - left half matches the before object at the mapped time, right half the after object
  - both citations are kind recording and resolve
  - labels, if burned, are substrings of OCR or are the timestamp text
  - offline is true

outputs:
  - side-by-side mp4
  - edl.json
  - script json with two citations on the beat

refresh_policy: rebuild when either object or the manifest changes

crafts:
  - video-edit
  - frame-still
