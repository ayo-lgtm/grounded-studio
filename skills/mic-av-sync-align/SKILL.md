# skill: mic-av-sync-align
version: 1.0.0
offline: true
area: capture
job: Measure the offset between the mic track and the capture audio locally, then shift one track.

inputs_required:
  - recording with a reference audio track
  - separate mic recording captured in the same session
inputs_optional:
  - a clap or tone the operator performed, visible in both streams

truth_source: the two local waveforms

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Extract mono wavs with local ffmpeg.
  - Estimate offset with a local cross-correlation or by aligning a clap transient. Write offset_ms and the method.
  - Shift the mic with ffmpeg. Do not time-stretch speech.
  - If absolute offset exceeds 500ms, stop for a person. Do not guess a second alignment.
  - Mux the aligned mic. Keep the original file. The aligned file is a new object with its own hash.

visual_grammar:
  - picture timestamps stay on the capture clock
  - no waveform graphic is required in the briefing

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud audio alignment APIs
  - replacing the voice with TTS to hide a sync error
  - dropping the mic and pretending the camera audio is the mic

qa_checks:
  - offset_ms is present and the method is recorded
  - aligned duration matches the capture within one frame after the shift
  - original objects are unchanged
  - offline is true

outputs:
  - aligned recording
  - sync.json with offset_ms

refresh_policy: recompute when either source file changes; do not reuse offset_ms across sessions

crafts:
  - av-sync
  - screen-ingest
