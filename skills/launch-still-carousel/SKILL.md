# skill: launch-still-carousel
version: 1.0.0
offline: true
area: slideshow
job: Play a short carousel of launch screenshots that were attached or extracted from the recording.

inputs_required:
  - at least two stills with citations
  - launch document or transcript
inputs_optional:
  - launch-teaser-cut storyboard order

truth_source: the stills and the launch sentences

story_beats:
  - Plan the sequence from cited frames before rendering. One still per beat. Order follows source time unless the parent storyboard already fixed the order.
  - Extract every still with local ffmpeg from a cited timestamp, or use an attached screenshot already stored on MinIO.
  - Caption text is the spoken line or the OCR label for that frame. It is not a new sentence.
  - Hold length equals the cited spoken span. If the frame has no speech, hold 2500ms and say so in the EDL.
  - Assemble with local ffmpeg concat of stills, or the deck renderer only when the skill names house layouts. No public render endpoint.
  - Use the storyboard order when it exists. Otherwise use timestamp order.
  - Each still gets the sentence that cites it. If a still has no sentence, it does not enter the carousel.
  - Total holds should land between 15 and 25 seconds when this carousel is the teaser companion. If the sentences are longer, do not speed them up; fail and point at launch-teaser-cut.
  - On-screen words are the sentence or the OCR copy, not a rewritten slogan.

visual_grammar:
  - renderer: slideshow of cited stills via local ffmpeg, unless a line below names the deck renderer
  - pixels are source frames only
  - a crop zoom is allowed only toward a cited click box and only inside the frame
  - type on a card, if any, uses house.py tokens
  - layout: step
  - silence unless a local TTS skill is applied later to the accepted sentences
  - house caption bar for the sentence

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - app-store imagery that was not captured
  - music
  - cloud carousel templates

qa_checks:
  - every still resolves
  - every caption cites a block or a transcript span
  - no still lacks a sentence
  - offline is true

outputs:
  - mp4
  - storyboard.json
  - script json

refresh_policy: rebuild when a still or its sentence changes

crafts:
  - slideshow-advance
  - teaser-storyboard
  - frame-still
