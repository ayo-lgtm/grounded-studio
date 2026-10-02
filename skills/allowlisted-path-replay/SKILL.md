# skill: allowlisted-path-replay
version: 1.0.0
offline: true
area: capture
job: Replay a path with Playwright only against hostnames listed in the on-disk internal allowlist.

inputs_required:
  - path steps already in a cited document or prior recording
  - worker allowlist file of internal staging hostnames
inputs_optional:
  - storage state captured earlier on the same internal host

truth_source: the allowlist file and the cited steps; the replay video is a new recording of those steps

pipeline_steps:
  - Write the object only to localhost or company MinIO. Record bucket, key, sha256, byte length, and duration in manifest.json.
  - Do not open a socket to a public host. If a step would need one, mark that step forbidden and fail.
  - Load the allowlist from the worker filesystem. It is not fetched from the public internet.
  - Parse every URL the path will open. If the host is not on the allowlist, fail before launch.
  - Run Playwright on the worker, headed or headless, against that internal host only. The host must resolve inside the company network.
  - Record video to a local file, then ingest it with screen-capture-ingest.
  - The script of steps is the cited source steps. Do not add clicks to get past an unexpected screen. Stop and cite the frame where the path diverged.
  - This skill is the capture contract for the v1.5 path-replay idea. The id is allowlisted-path-replay.

visual_grammar:
  - output is a normal recording object
  - no annotated arrows

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - any host that is not on the allowlist
  - public internet egress, including a CDN hostname that is not listed
  - cloud browser farms
  - continuing past a divergence by improvising UI steps

qa_checks:
  - every requested host is in the allowlist file
  - Playwright trace and video stay on MinIO or local disk
  - divergence stops the run and cites the last matching step
  - offline is true in the sense of no public egress; internal staging on the allowlist is the only remote

outputs:
  - replay recording
  - manifest.json
  - step-result.json

refresh_policy: re-run only when the cited steps or the allowlist change; a failed divergence is not auto-retried

crafts:
  - screen-ingest
