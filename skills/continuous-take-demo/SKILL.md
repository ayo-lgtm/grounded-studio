# skill: continuous-take-demo
version: 1.0.0
offline: true
area: video
job: Cut a real capture as one continuous take, where every beat boundary keeps a survivor from the previous beat.

inputs_required:
  - recording stored on localhost or company MinIO
inputs_optional:
  - transcript from local faster-whisper

truth_source: recording frames and the local transcript

story_beats:
  - Design the boundaries before the pictures. Each boundary names the survivor that is already on screen.
  - A survivor is the same screen label carried forward, or the outgoing source frame held under the next title.
  - Do not open the next beat on a blank card. A card that replaces the picture is a slideshow cut and fails.
  - Order stays source order. Do not reorder beats to invent a camera move.
  - Rests are allowed. Uniform cadence, where every cut is the same length, is a warning.
  - Hook only when the speaker says what the recording is for. Otherwise start on the first real step.
  - Write the carry record into the edit before render. Local ffmpeg holds the outgoing frame; it does not invent pixels.
  - Chapter titles are labels already on the capture or in the transcript. They sit on the surviving frame.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - tool: local ffmpeg
  - continuity mode: carry-boundary
  - hold about half a second of the outgoing frame at each boundary
  - chrome for any type uses house.py

qa_checks:
  - offline is true
  - every boundary has a non-empty survivor
  - no boundary kind is replace
  - boundary count is one less than the cut count when there are two or more cuts
  - citations stay inside the source duration
  - no beat carries style, color, font, css, theme, or background

outputs:
  - script json with edit.continuity
  - edl.json
  - mp4

refresh_policy: a new capture rebuilds boundaries whose spans moved

crafts:
  - carry-boundary
  - video-edit
  - edl-cut

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
