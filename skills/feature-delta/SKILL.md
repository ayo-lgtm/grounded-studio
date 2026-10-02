# skill: feature-delta
version: 1.0.0
offline: true
job: Explain what changed since a parent walkthrough using a new clip and/or changelog document.

inputs_required:
  - parent briefing
inputs_optional:
  - recording (short)
  - changelog document

truth_source: parent accepted script + new sources only

visual_grammar:
  - renderer: recording editor
  - layouts: step, and statement only when a changelog block is cited
  - unchanged parent beats stay verbatim

story_beats:
  - what is unchanged
  - what changed
  - how to switch / migrate if the source says so

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render; no public internet egress
  - rewriting unchanged chapters in a way that drops citations
  - claiming a change not in the new source

qa_checks:
  - new claims cite the new asset
  - unchanged beats keep parent citation ids or equivalent spans

outputs:
  - delta script
  - mp4 of changed chapters plus links to parent chapters

refresh_policy: this skill is itself a refresh
