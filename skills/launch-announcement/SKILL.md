# skill: launch-announcement
version: 1.0.0
offline: true
job: Turn a launch or announcement writeup into a clean internal presentation.

inputs_required:
  - document
inputs_optional:
  - screenshots as attachments

truth_source: document + attached images only

story_beats:
  - what shipped
  - who it is for
  - what changes for them
  - when
  - how to try
  - FAQ copied from the doc

visual_grammar:
  - renderer: deck
  - layouts: cover, statement, ask
  - attached screenshots can sit in a later master; v1 shows the source sentence
  - chrome comes from house.py

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render; no public internet egress
  - new dates, pricing, or promises
  - translating a "maybe" in the doc into a commitment

qa_checks:
  - dates and proper nouns copied verbatim
  - every slide cites a block

outputs:
  - deck html
  - optional narration
  - announcement md

refresh_policy: new doc version replaces beats whose source blocks changed
