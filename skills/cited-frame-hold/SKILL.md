# skill: cited-frame-hold
version: 1.0.0
offline: true
area: slideshow
job: Hold a single cited frame for the spoken duration of its beat.

inputs_required:
  - one recording citation
  - the transcript line or accepted beat text for that span
inputs_optional:
  - a click box inside the span for a static crop

truth_source: that one frame and that one sentence

story_beats:
  - Plan the sequence from cited frames before rendering. One still per beat. Order follows source time unless the parent storyboard already fixed the order.
  - Extract every still with local ffmpeg from a cited timestamp, or use an attached screenshot already stored on MinIO.
  - Caption text is the spoken line or the OCR label for that frame. It is not a new sentence.
  - Hold length equals the cited spoken span. If the frame has no speech, hold 2500ms and say so in the EDL.
  - Assemble with local ffmpeg concat of stills, or the deck renderer only when the skill names house layouts. No public render endpoint.
  - Extract one frame. Do not animate it.
  - A crop is allowed only when a click box exists, and the crop is static for the whole hold.
  - Duration equals the spoken span. Audio is the original slice, not new TTS, unless a later duck skill is asked.
  - If the sentence and the frame disagree, fail. Do not pick a different frame to match the sentence.

visual_grammar:
  - renderer: slideshow of cited stills via local ffmpeg, unless a line below names the deck renderer
  - pixels are source frames only
  - a crop zoom is allowed only toward a cited click box and only inside the frame
  - type on a card, if any, uses house.py tokens
  - layout: step
  - no motion graphics, lower thirds, or progress bars

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a second frame
  - looping a different moment under the sentence
  - generated background

qa_checks:
  - output duration matches the citation within 100ms
  - frame hash matches the source
  - audio slice matches the source samples for that span
  - offline is true

outputs:
  - mp4
  - poster.png of the same frame
  - script json with one beat

refresh_policy: rebuild when the citation moves

crafts:
  - frame-still
  - slideshow-advance
