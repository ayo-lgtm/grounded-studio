# skill: executive-business-review
version: 1.0.0
job: Produce a concise leadership-ready business review from mixed workbook, document, PDF, and recording evidence.

inputs_required:
  - at least one grounded source
inputs_optional:
  - workbook
  - supporting documents
  - recording
  - previous review
  - metric policy
  - audience

crafts_required:
  - workbook-analysis when workbook is present
  - variance-analysis when comparisons are requested
  - chart-selection
  - source-visualization
  - data-narration
  - consulting-action-title
  - slide-grammar

## Evidence hierarchy
- numbers: prefer workbook cells/formulas
- authored explanations: document/PDF text
- product behavior: recording
- conflicts: surface the conflict; never silently choose the more convenient source

## Leadership compression
The review may be shorter than the source pack, but compression cannot delete required facts, reverse meaning, hide a material adverse variance, or detach a claim from evidence.

Lead with decisions and business state, not an agenda slide.
Each slide should answer one leadership question.

## Common questions
- What changed?
- Against what benchmark?
- Where is the variance concentrated?
- What evidence explains it?
- What risk is documented?
- What decision or action is actually requested?

## Mixed-source QA
- same metric name must resolve to a consistent definition or be disambiguated;
- reporting periods must be aligned;
- contradictions are surfaced;
- every numeric claim prefers cell lineage when a workbook source exists;
- screenshots/video frames are used when the visual source itself matters.

outputs:
  - executive deck
  - optional narrated video
  - evidence appendix
  - conflict log
  - calculation audit
