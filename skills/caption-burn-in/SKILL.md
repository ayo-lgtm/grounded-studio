# skill: caption-burn-in
version: 1.0.0
offline: true
area: video
job: Burn captions that are the spoken line, timed to the local transcript, onto a real cut.

inputs_required:
  - recording or an accepted cut on localhost or company MinIO
  - word-timed transcript from local faster-whisper
inputs_optional:
  - glossary for spellings already in the transcript
  - line-break hints; they may not change words

truth_source: transcript words; captions are not a paraphrase

story_beats:
  - Group words into cues of at most two lines and 42 characters per line. Break on clause boundaries when the transcript has punctuation.
  - Cue start and end are the first and last word timestamps. Do not shift a cue to fit music.
  - Cue text is the words in order. Glossary may correct a spelling only when the glossary term is the documented form of a word already recognized.
  - Write WebVTT. Then burn with the recording editor caption bar from house.py, or ffmpeg subtitles using the house caption colors already in house.py. Do not invent a palette.
  - If a word was removed by filler-word-cut, omit it from the cue and keep the neighboring words.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - caption bar uses house.py caption and caption-ink tokens
  - no style, color, font, css, theme, or background key on the beat
  - safe area is inside the frame; overflow fails rather than shrinking type ad hoc

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - paraphrasing, translating, or adding a word the speaker did not say
  - cloud caption APIs
  - karaoke effects, emoji, or a speaker name that is not in the source metadata

qa_checks:
  - every cue token appears in the transcript for that time range, ignoring filler already cut
  - cue times fall inside the source duration and do not overlap by more than 80ms
  - a spot check of three cues matches the audio by ear on the worker, or the job stays in review
  - burned text does not clip the frame in a local PNG still of the first, middle, and last cue
  - offline is true

outputs:
  - captions.vtt
  - mp4 with burned captions
  - script json whose beat text equals the cue text

refresh_policy: rebuild cues when the transcript or the cut EDL changes; accepted cue text stays if the word span still matches

crafts:
  - caption-track
  - video-edit
