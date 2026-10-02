# craft: quality-gate
version: 1.0.0
offline: true
used_by: offline-quality-gate, offline-refine-loop, grounded-qa

job: Score a briefing locally before anyone shares it.

rules:
  - Fail on a missing citation, an empty required KPI, a missing survivor, or clipped audio.
  - Warn on uniform cadence and on a take with no rest.
  - Measurements come from the script and from local ffmpeg.
  - Write quality.json next to the render.

forbidden:
  - any external HTTP API or hosted media probe
  - public internet egress
  - shipping a fail
