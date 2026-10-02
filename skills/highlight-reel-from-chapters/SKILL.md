# skill: highlight-reel-from-chapters
version: 1.0.0
offline: true
area: video
job: Assemble a reel from chapters a human already marked keep, in their original order.

inputs_required:
  - accepted chaptered cut with recording citations
  - keep flags on chapters, set by a person in the product
inputs_optional:
  - a max duration in seconds, used only to refuse an over-long selection rather than to auto-drop chapters

truth_source: kept chapters of the parent briefing; no new claims

story_beats:
  - Select chapters whose keep flag is true. Ignore the rest.
  - Preserve parent order and parent citation ids.
  - If the user passed a max duration and the selection is longer, fail and list the chapter durations. Do not drop the last chapter quietly.
  - Concat the kept spans with local ffmpeg. No new narration.
  - The reel title is the parent title plus the word Highlight only if the operator set that title; otherwise reuse the parent title.

visual_grammar:
  - renderer: recording editor
  - layout: step
  - no new cards unless chapter-card-overlay already baked them into a kept span
  - picture is parent pixels only

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - choosing highlights by model taste when keep flags are absent
  - writing a new hook line
  - pulling a moment from outside a kept chapter

qa_checks:
  - every output beat maps to a parent beat with keep true
  - order matches parent ord
  - no output text that is not parent text
  - if max duration is set, either the reel fits or the job failed
  - offline is true

outputs:
  - reel mp4
  - edl.json
  - script json with parent citation ids

refresh_policy: rebuild when keep flags or parent spans change

crafts:
  - video-edit
  - edl-cut
  - watch-footage
