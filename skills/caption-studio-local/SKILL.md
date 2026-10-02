# skill: caption-studio-local
version: 1.0.0
offline: true
area: video
job: Write captions from the local transcript and burn or sidecar them on the box.

inputs_required:
  - a local faster-whisper transcript, or an accepted beat whose text is that transcript
inputs_optional:
  - the cut mp4 for a burn-in

truth_source: the transcript line for that span

story_beats:
  - One caption cue per kept spoken span.
  - Cue text is the transcript line. Do not paraphrase.
  - Write captions.vtt timed to the output clock.
  - A burn-in uses the house caption bar and local ffmpeg drawtext.
  - Do not send the audio to a caption vendor.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - caption bar uses house caption tokens

qa_checks:
  - offline is true
  - every cue text is the beat text
  - cue times fall inside the output duration
  - engine is local

outputs:
  - captions.vtt
  - optional burned mp4

refresh_policy: rewrite cues whose transcript spans moved

crafts:
  - caption-track
  - video-edit

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
