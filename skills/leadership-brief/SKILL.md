# skill: leadership-brief
version: 1.0.0
offline: true
job: Compile a written document into a sparse leadership deck and optional short narration.

inputs_required:
  - document
inputs_optional: []

truth_source: document blocks

story_beats:
  - situation
  - recommendation or ask
  - evidence
  - risks
  - next step
  Omit a beat if the document does not contain it. Do not fill the hole.

visual_grammar:
  - renderer: deck
  - layouts: cover, statement, risk, ask
  - the sentence on the slide is the source sentence
  - chrome comes from house.py

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render; no public internet egress
  - new recommendations
  - benchmarking against data not in the doc
  - "in conclusion we should" if the author did not say so

qa_checks:
  - every slide title and body sentence cites a block_id
  - numbers in slides equal numbers in cited blocks

outputs:
  - deck html
  - optional voiced slide video
  - one-pager md

refresh_policy: recompile from a new doc version; diff blocks
