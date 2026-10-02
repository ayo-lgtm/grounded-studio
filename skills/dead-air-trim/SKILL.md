# skill: dead-air-trim
version: 1.0.0
offline: true
area: video
job: Remove measured silence from a real recording while keeping every spoken claim and its timestamps.

inputs_required:
  - recording on localhost or company MinIO
  - audio energy or silence map computed locally with ffmpeg astats or silencedetect
inputs_optional:
  - local transcript with word timestamps
  - operator threshold override inside the documented range

truth_source: the recording's own audio; silence is a measured gap, not a guess

story_beats:
  - Run silencedetect locally. Default gap is 800ms at -35 dB. Record the command and the threshold in the EDL note.
  - Subtract any gap that overlaps a transcript word. Speech wins over the energy detector.
  - Do not trim inside a word. Snap cuts to word edges when a transcript exists, else to the detector edges.
  - Leave a 120ms handle before and after speech so words are not clipped.
  - Write the kept ranges to edl.json with reason dead-air. Do not add frames.
  - Render with local ffmpeg. Store the silence map next to the artifact.

visual_grammar:
  - renderer: recording editor
  - layout: step on each kept spoken span
  - no card, zoom, or caption is added by this skill
  - picture is the source raster for the kept times only

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - trimming a pause that contains a cited word
  - tightening a gap below the recorded threshold to make the cut feel faster
  - replacing silence with music, room tone from another file, or a generated hold

qa_checks:
  - every transcript word from the parent appears in some kept span
  - no kept span is shorter than the word it contains
  - removed ranges match the silence map and do not overlap word times
  - output has no sample that was not in the source file
  - offline is true and no audio left the host

outputs:
  - edl.json
  - silence-map.json
  - trimmed mp4
  - script json whose citations use original source timestamps, plus a map to output times

refresh_policy: re-run when the source file or the threshold changes; do not reuse a silence map from a different file

crafts:
  - video-edit
  - edl-cut
