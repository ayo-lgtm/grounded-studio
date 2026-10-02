# skill: chapter-still-advance
version: 1.0.0
offline: true
area: slideshow
job: Hold one cited frame per accepted chapter for the length of that chapter's speech.

inputs_required:
  - accepted chapters with recording citations
  - recording
inputs_optional:
  - chapter titles for cards

truth_source: chapter citations

story_beats:
  - Plan the sequence from cited frames before rendering. One still per beat. Order follows source time unless the parent storyboard already fixed the order.
  - Extract every still with local ffmpeg from a cited timestamp, or use an attached screenshot already stored on MinIO.
  - Caption text is the spoken line or the OCR label for that frame. It is not a new sentence.
  - Hold length equals the cited spoken span. If the frame has no speech, hold 2500ms and say so in the EDL.
  - Assemble with local ffmpeg concat of stills, or the deck renderer only when the skill names house layouts. No public render endpoint.
  - Pick the frame at the chapter's first non-silent timestamp.
  - Hold for the chapter's spoken duration after filler and dead air already removed, or the raw span if those cuts do not exist.
  - A title card is allowed only by calling the same rule as chapter-card-overlay: the title is the accepted chapter title, 1.5s, house chrome.
  - Do not reorder chapters.

visual_grammar:
  - renderer: slideshow of cited stills via local ffmpeg, unless a line below names the deck renderer
  - pixels are source frames only
  - a crop zoom is allowed only toward a cited click box and only inside the frame
  - type on a card, if any, uses house.py tokens
  - layout: step
  - card then still, per chapter

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - choosing a prettier frame outside the chapter span
  - writing a new chapter title

qa_checks:
  - one still per chapter
  - frame time lies inside the chapter citation
  - order matches chapter ord
  - offline is true

outputs:
  - mp4
  - edl.json
  - script json

refresh_policy: rebuild a chapter when its citation or title changes

crafts:
  - slideshow-advance
  - frame-still
