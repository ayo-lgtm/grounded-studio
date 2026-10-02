# skill: click-zoom-edit
version: 1.0.0
offline: true
area: video
job: Punch in on a real click by cropping source pixels around a detected click box.

inputs_required:
  - recording on localhost or company MinIO
  - click-region index with x, y, t_ms, and frame size
inputs_optional:
  - local OCR label for the control under the click

truth_source: click coordinates measured on the capture, and the pixels at that time

story_beats:
  - For each click, confirm t_ms falls inside a beat that cites the recording.
  - Build a crop rectangle centered on the click, clamped to the frame. Default is 45 percent of frame width. Record the rectangle in the EDL.
  - Hold the wide shot until 400ms before the click, then cut to the crop, then return when the next spoken clause ends or after 2.5s, whichever is sooner.
  - If two clicks land inside one sentence, zoom to the union of the boxes instead of oscillating.
  - Scale the crop with local ffmpeg. Interpolation may blur source pixels. It may not invent UI.
  - Optional label under the zoom is the OCR string of the control, or nothing. Do not name a control the detector missed.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - zoom is a crop of the source frame, not a callout drawn in a design tool
  - house.py supplies the caption bar only if caption-burn-in runs later
  - this skill sets no color, font, or CSS

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - zooming toward a control that has no click event
  - drawing a synthetic cursor, highlight ring, or arrow
  - using a cloud reframer or generative outpaint to fill the crop

qa_checks:
  - every zoom rectangle is inside the source frame
  - every zoom t_ms matches a click-region row
  - OCR label, if present, is a substring of the local OCR read at that timestamp
  - output frames outside zoom windows match the source frame at the mapped time
  - offline is true

outputs:
  - edl.json with crop rects
  - mp4
  - script json citing recording spans

refresh_policy: recompute crops when the click index or frame size changes; keep beats whose click rows still exist

crafts:
  - video-edit
  - edl-cut
  - vision-read-screen
