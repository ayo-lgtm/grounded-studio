# skill: before-after-still-show
version: 1.0.0
offline: true
area: slideshow
job: Show the before still, then the after still, from an accepted snapshot pair.

inputs_required:
  - before.png and after.png from before-after-snapshot-pair
  - diff.json
inputs_optional:
  - a transcript line that mentions the change, cited

truth_source: the pair manifest

story_beats:
  - Plan the sequence from cited frames before rendering. One still per beat. Order follows source time unless the parent storyboard already fixed the order.
  - Extract every still with local ffmpeg from a cited timestamp, or use an attached screenshot already stored on MinIO.
  - Caption text is the spoken line or the OCR label for that frame. It is not a new sentence.
  - Hold length equals the cited spoken span. If the frame has no speech, hold 2500ms and say so in the EDL.
  - Assemble with local ffmpeg concat of stills, or the deck renderer only when the skill names house layouts. No public render endpoint.
  - Beat one is the before frame. Beat two is the after frame. Do not insert a transition frame.
  - Caption is the OCR diff of labels that appeared or disappeared, or the cited transcript line. If neither exists, the caption is the timestamps only.
  - Hold each still for the cited speech or for 2500ms.
  - Do not label the pair improved.

visual_grammar:
  - renderer: slideshow of cited stills via local ffmpeg, unless a line below names the deck renderer
  - pixels are source frames only
  - a crop zoom is allowed only toward a cited click box and only inside the frame
  - type on a card, if any, uses house.py tokens
  - layout: step
  - full frame, not a designed split, unless side-by-side-before-after already produced a composed still and this skill is told to hold that one file

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a third still
  - generative morph
  - swapping order

qa_checks:
  - hashes match the pair files
  - before plays first
  - caption strings come from OCR diff, transcript, or timestamps
  - offline is true

outputs:
  - mp4
  - script json with two recording citations

refresh_policy: rebuild when the pair changes

crafts:
  - slideshow-advance
  - frame-still
