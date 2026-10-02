# skill: identity-consistency-lock
version: 1.0.0
offline: true
area: video
job: Record the product screens a cut actually shows, so later beats do not invent a new chrome.

inputs_required:
  - a recording whose cuts carry screen labels from the capture
inputs_optional:
  - local OCR labels when a screen label is missing

truth_source: screen labels on the capture, or local OCR of a cited frame

story_beats:
  - List the distinct screen labels in source order. That list is the identity of the film.
  - A later beat may show a screen only if the capture already showed it, or the speaker named it.
  - Do not swap in a screenshot from another product.
  - Do not call a hosted identity or character library.
  - The lock is a note on the script. It does not generate a face or a UI.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - pixels stay the source frames

qa_checks:
  - offline is true
  - every screen in the identity list appears on a cut
  - no beat names a screen that is absent from the list and absent from the transcript
  - no style key

outputs:
  - script.identity
  - edl.json

refresh_policy: rebuild the list when cuts change

crafts:
  - screen-ingest
  - local-ocr

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
