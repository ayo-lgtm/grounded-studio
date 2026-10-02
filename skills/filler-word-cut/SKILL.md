# skill: filler-word-cut
version: 1.0.0
offline: true
area: video
job: Cut filler tokens listed in the local transcript and leave every other word in place.

inputs_required:
  - recording on localhost or company MinIO
  - word-timed transcript from local faster-whisper
inputs_optional:
  - workspace filler list; default is um, uh, er, ah

truth_source: transcript token timings; a word is filler only if it is on the list and is its own token

story_beats:
  - Mark tokens whose normalized form is on the filler list. Do not mark a word that merely contains those letters.
  - Expand each cut by 40ms on either side only when that pad contains no other word.
  - Write edl.json with reason filler. Concat the complement with local ffmpeg.
  - Captions built later must drop the same tokens.
  - If more than 15 percent of spoken duration would be removed, stop and leave the cut in review with the list visible. Do not auto-accept an aggressive cut.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - picture and non-filler audio are source samples only

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cutting false starts, repeats, or asides that are not on the filler list
  - rewriting the sentence after the cut
  - cloud disfluency models

qa_checks:
  - every removed token is on the filler list
  - every non-filler token survives in order
  - removed duration share is reported, and the job is blocked above 15 percent until a person accepts it
  - offline is true

outputs:
  - edl.json
  - mp4
  - filler-report.json
  - script json

refresh_policy: re-cut when the transcript or the filler list changes

crafts:
  - video-edit
  - edl-cut
  - caption-track
