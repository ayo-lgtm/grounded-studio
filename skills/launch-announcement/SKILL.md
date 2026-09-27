# skill: launch-announcement
version: 1.0.0
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
  - slides
  - use attached screenshots as-is
  - do not generate product UI

forbidden:
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
