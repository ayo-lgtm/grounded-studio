# skill: sop-training
version: 1.0.0
job: Produce a followable SOP from a recording and/or document.

inputs_required: []
inputs_optional:
  - recording
  - document
note: at least one of recording or document is required

truth_source: whichever sources were provided

story_beats:
  - purpose
  - prerequisites
  - numbered steps
  - failure / rollback if present
  - owner if present

visual_grammar:
  - renderer: recording editor, same house style as product-walkthrough
  - layout: step
  - one numbered step per spoken line; guide.md is that list

forbidden:
  - adding safety or compliance steps that are not in the source
  - merging two steps into one if the source numbered them separately

qa_checks:
  - steps numbered continuously
  - each step has a citation

outputs:
  - guide.md
  - optional mp4
  - chapters

refresh_policy: new recording or doc; keep step ids stable when text is similar
