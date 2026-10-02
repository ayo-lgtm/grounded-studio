# skill: accessibility-audio-description
version: 1.0.0
offline: true
area: video
job: Add an audio-description track that speaks only UI changes local OCR can see between cited frames.

inputs_required:
  - recording on localhost or company MinIO
  - local OCR reads sampled at cuts and at click times
inputs_optional:
  - existing transcript to avoid talking over the speaker

truth_source: OCR diffs between frames; description text may not add intent

story_beats:
  - At each cut or click, diff the OCR strings. A description line lists labels that appeared or disappeared, using those strings.
  - Do not describe why the user clicked or what the feature means.
  - Place the line in a gap longer than the line's duration plus 200ms. If no gap exists, fail that line into review instead of ducking the speaker.
  - Speak the line with the pinned local Piper or Kokoro voice. Write one wav per line.
  - Mix onto a separate audio track so the original program stays intact.

visual_grammar:
  - renderer: recording editor
  - picture is unchanged
  - optional on-screen description uses the house caption bar and the same words as the wav
  - layout: step

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud audio-description services
  - inferring buttons that OCR did not read
  - talking over the primary speaker
  - emotional or promotional language

qa_checks:
  - every description noun is a substring of an OCR read at the cited time
  - description spans do not overlap transcript speech
  - program audio hash matches the input program audio
  - offline is true

outputs:
  - description.vtt
  - per-line wav
  - mp4 with a second audio track
  - script json

refresh_policy: rebuild lines whose OCR diff changed; leave lines whose reads still match

crafts:
  - tts-narration
  - local-ocr
  - vision-read-screen
