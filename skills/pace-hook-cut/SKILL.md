# skill: pace-hook-cut
version: 1.0.0
offline: true
area: video
job: Score the opening of an accepted cut so a real spoken hook is audible inside the first three seconds.

inputs_required:
  - accepted cut with transcript and EDL
inputs_optional:
  - a hook sentence already present in the transcript or a cited document

truth_source: existing beats and their citations; this skill only reorders the opening if the hook sentence already exists later

story_beats:
  - Find the earliest span whose transcript contains the hook sentence, or whose text equals the cited doc sentence.
  - If that span already starts at or before 3000ms of output time, write pace-report.json with status pass and do not recut.
  - If it starts later, move that span to the front only when it is a complete beat with its own citation. Do not slice a sentence.
  - Leave the remaining beats in their original order. Record the move in the EDL as reason hook.
  - If no hook sentence exists, fail closed. Do not write one.
  - Dead air before the hook is removed only by citing dead-air-trim ranges already computed. This skill does not invent a new silence threshold.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - no new title card unless chapter-card-overlay already produced one for that beat
  - local ffmpeg concat of the moved EDL

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - writing a hook the speaker did not say and the doc does not contain
  - trimming words to make the hook fit three seconds
  - adding a generated cold open

qa_checks:
  - output time 0 to 3000ms overlaps the hook beat, or the job failed
  - the hook beat's citation is unchanged
  - every parent beat still appears once
  - offline is true

outputs:
  - mp4
  - edl.json
  - pace-report.json
  - script json

refresh_policy: re-score when the parent EDL changes; a passing report is reused only if beat ids and times match

crafts:
  - video-edit
  - edl-cut
  - watch-footage
