# 08 — Build plan (job-internal)

## Phase 0 — box and policy
GPU workstation on corp network. IT written OK: no egress, SSO app. Pin Whisper, one 7B–14B instruct, embeddings, Piper. Compose: web, api, worker, postgres, redis, minio, ollama/vllm.

## Phase 1 — walkthrough loop (weeks 1–3)
Upload recording, transcribe, compile with product-walkthrough, citation QA, review UI, ffmpeg + captions, player with transcript. Exit: replace one recurring internal demo.

## Phase 2 — chat + sharing (week 4)
Embeddings, refuse-on-miss chat, workspace sharing, audit.

## Phase 3 — documents (weeks 5–6)
leadership-brief, launch-announcement, HTML deck, optional TTS.

## Phase 4 — Excel recurrence (weeks 7–8)
Cell index, weekly-ops-review, templates + diff, numeric QA.

## Phase 5 — localize + sop (weeks 9–10)
localize, sop-training, feature-delta.

## Phase 6 — harden
SSO enforced, egress firewall verified, backup drill, retention, job queue.

Later: path-replay, launch-teaser, k8s, mobile recorder, fine-tuning.
