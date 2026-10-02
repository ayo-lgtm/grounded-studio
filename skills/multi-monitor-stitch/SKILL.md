# skill: multi-monitor-stitch
version: 1.0.0
offline: true
area: capture
job: Tile recorded displays into one frame using the geometry the capture wrote down.

inputs_required:
  - one recording per display, or one recording with a display map
  - geometry: x, y, width, height per display from the capture manifest
inputs_optional:
  - a primary-display flag from the manifest

truth_source: the manifest geometry and the display recordings

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Refuse the job if any display lacks a rectangle in the manifest.
  - Place each recording on a canvas of the union rectangle with local ffmpeg overlay. Positions come from the manifest.
  - Do not scale a display to look bigger than its recorded pixels except a uniform integer scale applied to all of them and written in the EDL.
  - Audio is the primary display's audio, or the only audio track if there is one. Do not mix in a new track.

visual_grammar:
  - output is one raster built from the source rasters
  - empty canvas around displays stays black and is not filled with generated desktop

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - inventing a second monitor when the manifest lists one
  - rearranging displays to match a story
  - cloud multicam editors

qa_checks:
  - each source rectangle in the output matches that display's pixels
  - canvas size equals the union of the manifest rectangles
  - offline is true

outputs:
  - stitched mp4
  - edl.json
  - manifest for the new object

refresh_policy: rebuild when any display file or the geometry changes

crafts:
  - screen-ingest
  - edl-cut
