# craft: carry-boundary
version: 1.0.0
offline: true
used_by: continuous-take-demo, carry-boundary-verify, local-video-assembly, product-walkthrough

job: Keep a survivor on screen at every beat boundary.

rules:
  - Name the survivor before the render. It is the continuing screen label or the outgoing frame.
  - Hold that frame for a short beat so the next title sits on top of it.
  - A full-frame replacement is a failed boundary.
  - Local ffmpeg performs the hold. It does not paint a new scene.
  - Source in and out points stay the cited timestamps.

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind
  - a hosted video model, a generated transition, or a blank chapter card that hides the capture
