# skill: poster-frame-pick
version: 1.0.0
offline: true
area: video
job: Choose one cited source frame as the poster image for a briefing.

inputs_required:
  - recording on localhost or company MinIO
  - at least one recording citation
inputs_optional:
  - operator-chosen t_ms inside a citation

truth_source: a single frame of the source file

story_beats:
  - If the operator picked t_ms, extract that frame only when it lies inside a citation.
  - Otherwise take the frame at the start of the first step beat, after any hook card, so the poster shows the product rather than a title card.
  - Extract with local ffmpeg, one frame, PNG. Do not upscale with a model.
  - Run local OCR. The poster has no baked title. The briefing title stays in metadata.
  - Store the PNG beside the briefing in MinIO with the source timestamp in the object metadata.

visual_grammar:
  - no renderer change to the video
  - the poster is an unmodified frame
  - do not overlay type; the player chrome may show the briefing title separately

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - text-to-image posters
  - cropping out the UI to make a mood image
  - picking a frame outside every citation

qa_checks:
  - PNG dimensions match the source frame
  - pixel hash equals the source frame at t_ms
  - t_ms is inside a recording citation
  - offline is true

outputs:
  - poster.png
  - poster.json with t_ms and citation

refresh_policy: replace the poster when the chosen citation moves; do not keep a stale frame

crafts:
  - frame-still
