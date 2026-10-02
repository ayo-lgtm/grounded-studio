# skill: before-after-snapshot-pair
version: 1.0.0
offline: true
area: capture
job: Pair two frames whose local pixel diff shows a real change, and record which is earlier.

inputs_required:
  - recording, or two stills with timestamps
inputs_optional:
  - a user-proposed pair of timestamps to verify

truth_source: the two frames and a local pixel diff

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Extract both frames with local ffmpeg.
  - Compute a local pixel diff. Reject the pair if the diff is empty.
  - Earlier timestamp is before. Later is after. Do not swap them to improve the story.
  - Store both PNGs and diff.json with the bounding box of changed pixels. The box is evidence, not a caption.
  - Hand the pair to side-by-side-before-after or before-after-still-show.

visual_grammar:
  - no composition in this skill
  - frames are unmodified extracts

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - picking two similar frames and calling them a change
  - generative in-between frames
  - cloud visual-diff APIs

qa_checks:
  - both timestamps resolve in the recording
  - diff box is non-empty and inside the frame
  - before time is less than after time
  - offline is true

outputs:
  - before.png
  - after.png
  - diff.json

refresh_policy: rebuild when the recording or the proposed times change

crafts:
  - frame-still
  - vision-read-screen
