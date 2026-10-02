# skill: still-sequence-slideshow
version: 1.0.0
offline: true
area: slideshow
job: Auto-advance through cited frames of a recording in timeline order.

inputs_required:
  - recording
  - a list of citation timestamps or an accepted chapter list
inputs_optional:
  - transcript lines for captions

truth_source: recording frames and, for words, the transcript

story_beats:
  - Plan the sequence from cited frames before rendering. One still per beat. Order follows source time unless the parent storyboard already fixed the order.
  - Extract every still with local ffmpeg from a cited timestamp, or use an attached screenshot already stored on MinIO.
  - Caption text is the spoken line or the OCR label for that frame. It is not a new sentence.
  - Hold length equals the cited spoken span. If the frame has no speech, hold 2500ms and say so in the EDL.
  - Assemble with local ffmpeg concat of stills, or the deck renderer only when the skill names house layouts. No public render endpoint.
  - One frame per citation, at t_start_ms unless a click time inside the span is a better picture of the same citation. Record which time was used.
  - Do not add a frame to cover a topic the recording skipped.
  - Caption is the transcript line for that span, burned with the house caption bar or carried as VTT.
  - Hard cuts between stills. No dissolves that blend two UI states into a fake screen.

visual_grammar:
  - renderer: slideshow of cited stills via local ffmpeg, unless a line below names the deck renderer
  - pixels are source frames only
  - a crop zoom is allowed only toward a cited click box and only inside the frame
  - type on a card, if any, uses house.py tokens
  - layout: step
  - output mp4 is 1080p contain of the still

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - Ken Burns that reveals pixels outside the frame
  - stock transitions
  - a still from a different recording

qa_checks:
  - still count equals citation count
  - each PNG hashes to the source frame at the recorded time
  - caption tokens are transcript tokens for that span
  - offline is true

outputs:
  - slideshow mp4
  - edl.json
  - stills/
  - script json

refresh_policy: replace stills whose timestamps moved; keep the rest

crafts:
  - slideshow-advance
  - frame-still
  - caption-track
