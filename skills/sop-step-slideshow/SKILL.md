# skill: sop-step-slideshow
version: 1.0.0
offline: true
area: slideshow
job: Hold one cited frame per numbered SOP step, with the step sentence as the caption.

inputs_required:
  - SOP steps that already cite a recording
  - the recording
inputs_optional:
  - the sop-training guide.md

truth_source: the SOP step list and its citations

story_beats:
  - Plan the sequence from cited frames before rendering. One still per beat. Order follows source time unless the parent storyboard already fixed the order.
  - Extract every still with local ffmpeg from a cited timestamp, or use an attached screenshot already stored on MinIO.
  - Caption text is the spoken line or the OCR label for that frame. It is not a new sentence.
  - Hold length equals the cited spoken span. If the frame has no speech, hold 2500ms and say so in the EDL.
  - Assemble with local ffmpeg concat of stills, or the deck renderer only when the skill names house layouts. No public render endpoint.
  - One still per step, inside that step's citation.
  - Caption is the step sentence verbatim, including the number.
  - Do not merge steps. Do not add a safety step.
  - Order is the SOP order, which must already match increasing time.

visual_grammar:
  - renderer: slideshow of cited stills via local ffmpeg, unless a line below names the deck renderer
  - pixels are source frames only
  - a crop zoom is allowed only toward a cited click box and only inside the frame
  - type on a card, if any, uses house.py tokens
  - layout: step
  - teaching captions via the house caption bar
  - optional 1.5s card only if the step title is the step's own first line

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - rewording a step to fit the caption length; overflow fails the step
  - a frame from outside the step span

qa_checks:
  - step numbers are continuous
  - caption equals the step text
  - frame time is inside the step citation
  - offline is true

outputs:
  - mp4
  - vtt
  - script json

refresh_policy: rebuild steps whose text or citation changed; keep step ids when the text is similar

crafts:
  - slideshow-advance
  - frame-still
  - caption-track
