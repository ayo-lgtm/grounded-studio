# skill: screen-capture-ingest
version: 1.0.0
offline: true
area: capture
job: Accept a local screen recording, hash it, and store it on company MinIO with geometry and duration.

inputs_required:
  - a video file from the operator workstation or a worker-local capture path
inputs_optional:
  - display geometry note from the capture tool
  - workspace id and briefing id

truth_source: the file bytes and the container metadata read locally with ffprobe

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Reject the file if ffprobe cannot read a video stream locally.
  - Compute sha256 on the worker. Probe width, height, fps, duration_ms, and audio presence.
  - Put the object in MinIO under the briefing prefix. Store the manifest beside it.
  - Run the local malware scanner configured for the worker. Do not upload the file to a cloud scanner.
  - Hand the manifest to later capture skills. Do not transcribe in this skill.

visual_grammar:
  - no picture is generated
  - preview, if any, is a local ffmpeg frame at 0ms stored next to the object
  - no renderer

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - cloud ingest, cloud transcode, or a public pre-signed upload
  - executing macros or scripts embedded in a container
  - shrinking the file by dropping a stream without recording it in the manifest

qa_checks:
  - sha256 of the stored object matches the manifest
  - duration_ms is positive
  - bucket is the company MinIO endpoint configured for the worker, or a local path
  - offline is true

outputs:
  - manifest.json
  - object key
  - ffprobe.json

refresh_policy: a new upload is a new object; do not overwrite a key that already has an accepted briefing

crafts:
  - screen-ingest
