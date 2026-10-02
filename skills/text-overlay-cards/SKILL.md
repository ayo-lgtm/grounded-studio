# skill: text-overlay-cards
version: 1.0.0
offline: true
area: video
job: Composite short house labels on top of source frames. The picture stays visible.

inputs_required:
  - a cited frame or cut
  - label text copied from the transcript or the screen
inputs_optional:
  - none

truth_source: the transcript line or the on-screen label

story_beats:
  - The card is a small label, not a full-frame plate.
  - Text is the spoken line or the screen title. Do not write a new sentence.
  - Draw it with local ffmpeg drawtext using house caption colors.
  - The underlying pixels remain the source frame.
  - Do not use a hosted overlay or a slide product.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - type uses house caption ink on a caption box
  - the frame is otherwise untouched

qa_checks:
  - offline is true
  - overlay text is a substring of the transcript or the screen label for that span
  - the frame hash still matches the source except for the label region
  - no style key on the beat

outputs:
  - mp4 with the label burned locally
  - edl.json

refresh_policy: replace the label when the cited line changes

crafts:
  - caption-track
  - video-edit

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
