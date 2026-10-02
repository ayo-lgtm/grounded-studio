# skill: storyboard-from-chapters
version: 1.0.0
offline: true
area: video
job: Build a panel board from cited chapters. One panel per kept span, source order.

inputs_required:
  - recording
  - local transcript or an accepted chapter list
inputs_optional:
  - screen labels already on the capture

truth_source: recording timestamps and transcript lines

story_beats:
  - One panel per kept cut, in source order.
  - Panel title is the screen label or the spoken line. Do not invent a scene name.
  - The board is storyboard.html from the recording editor. It is not a generated image.
  - A carry hold, when the cut uses one, is a panel that names the survivor.
  - Do not add a panel for a topic the recording skipped.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - stills are source frames via local ffmpeg

qa_checks:
  - offline is true
  - panel count matches kept cuts
  - each panel cites a timestamp inside the source
  - no generated still

outputs:
  - storyboard.html
  - edl.json
  - script json

refresh_policy: rebuild panels whose timestamps moved

crafts:
  - frame-still
  - video-edit

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
