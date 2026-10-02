# skill: local-video-assembly
version: 1.0.0
offline: true
area: video
job: Assemble accepted cuts, carry holds, and captions into one file with local ffmpeg.

inputs_required:
  - an edit decision list whose rows cite source in and out points
  - the source recording on localhost or company MinIO
inputs_optional:
  - a local voice mix

truth_source: the EDL and the source file

story_beats:
  - Concat only the spans the EDL names, in listed order.
  - Re-encode a span when the cut is not keyframe-aligned. Codecs match across clips so the concat is one file.
  - Carry holds are frozen outgoing frames, not new shots.
  - Audio, when present, is the source bed ducked under a local voice, or the source bed alone.
  - No cloud transcode and no stock insert.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - tool: local ffmpeg concat

qa_checks:
  - offline is true
  - every clip maps to an EDL row
  - output duration matches the sum of row durations within one frame
  - no clip comes from a generated source

outputs:
  - mp4
  - edl.json

refresh_policy: replace clips whose in or out points moved

crafts:
  - video-edit
  - edl-cut
  - carry-boundary

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, Scenario, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - installing a remote skill pack or connecting a hosted MCP
