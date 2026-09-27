# skill: leadership-brief
version: 1.0.0
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
  - 6 to 12 slides
  - one idea per slide
  - large number only if the number exists in the document
  - no stock photos
  - no decorative charts that are not in the source

forbidden:
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
