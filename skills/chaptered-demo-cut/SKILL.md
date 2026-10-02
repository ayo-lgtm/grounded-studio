# skill: chaptered-demo-cut
version: 1.0.0
offline: true
area: video
job: Cut a real screen recording into timeline-ordered chapters that follow the spoken task changes.

inputs_required:
  - recording stored on localhost or company MinIO
inputs_optional:
  - transcript from local faster-whisper, produced on the worker when missing
  - document that only confirms a name already visible or spoken
  - accepted chapter list from a prior run

truth_source: recording frames and transcript; a document may not add a step

story_beats:
  - Read the transcript in time order before opening the editor. Mark a chapter where the speaker changes task or the screen changes route.
  - Write a one-line outline of chapters with draft timestamps. Do not render until every chapter has a citation span.
  - Hook chapter only when the speaker says what the recording is for, or a cited doc block says it. Otherwise start on the first real step.
  - One chapter per task. Order is increasing t_start_ms. Do not reorder for pacing.
  - Chapter title is the on-screen label from local OCR, or the speaker's name for that screen, copied as text. Do not invent a feature name.
  - Keep the spoken line that carries the step. Silence-only spans are not chapters.
  - Recap only if the speaker recaps. A next action only if the speaker or the cited doc states one.
  - Write edl.json first. Each row is clip id, source object, t_in_ms, t_out_ms, and the beat it serves.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - tool: local ffmpeg concat of the kept spans; re-encode a span only when the cut is not keyframe-aligned
  - chapter card, when used, is house.py chrome; this skill does not set color, font, or CSS
  - scale to 1080p from source pixels only
  - click zoom, caption burn-in, and TTS ducking stay in their own skills; the EDL keeps source timestamps so they can attach

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - naming a control that local OCR or the transcript cannot ground
  - inventing keyboard shortcuts
  - reordering steps to improve the story
  - text-to-video or any generated frame between cuts

qa_checks:
  - offline is true and the worker log shows no public-egress attempt
  - every beat has a recording citation with t_start_ms and t_end_ms inside the source duration
  - chapter starts are strictly increasing
  - each chapter title is a substring of the OCR text or the transcript for that span
  - EDL in and out points match the citations
  - mp4 duration equals the sum of kept spans within one frame
  - no beat carries style, color, font, css, theme, or background

outputs:
  - script json
  - edl.json
  - chapters
  - mp4
  - vtt of kept spoken lines
  - guide.md with one step per chapter

refresh_policy: a new clip dirties chapters whose spans moved or vanished; accepted beats whose citations still resolve stay verbatim

crafts:
  - video-edit
  - edl-cut
  - watch-footage
