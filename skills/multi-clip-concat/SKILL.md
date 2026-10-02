# skill: multi-clip-concat
version: 1.0.0
offline: true
area: video
job: Join accepted clips in cited order into one recording-editor timeline.

inputs_required:
  - two or more recordings or accepted cuts on localhost or company MinIO
  - an ordered list of clip ids supplied by the user or by an accepted script
inputs_optional:
  - per-clip chapter lists to preserve

truth_source: the clips and the stated order; the skill does not choose a better order

story_beats:
  - Confirm every object exists in local storage and hashes match the manifest.
  - Normalize frame rate and sample rate with local ffmpeg only when they differ. Record the conversion in the EDL. Do not retime speech.
  - Concat in the given order with the concat demuxer.
  - Shift citations into the output timeline and keep a map back to each source t_ms.
  - Insert nothing between clips: no bumper, no music, no generated transition. A hard cut is the join.
  - If a clip is missing, fail the job. Do not skip it.

visual_grammar:
  - renderer: recording editor
  - layout: step for each surviving beat, statement only when the source beat was statement
  - output geometry is the first clip's geometry unless a later safe-scale skill runs
  - house chrome is unchanged

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - crossfades that mix unrelated pixels into a new image
  - reordering clips by topic similarity
  - dropping a clip to hit a duration target
  - pulling a clip from outside MinIO or the local job directory

qa_checks:
  - output duration equals the sum of input durations within one frame, after documented normalization
  - every source citation appears in the map
  - clip order in the EDL equals the input order
  - hashes of inputs match the ingest manifest
  - offline is true

outputs:
  - concat mp4
  - edl.json
  - citation-map.json
  - script json

refresh_policy: re-concat when any member clip or the order list changes; do not reuse the map

crafts:
  - video-edit
  - edl-cut
