# skill: weekly-ops-review
version: 1.0.0
job: Recurring numeric briefing from a workbook that matches a saved template.

inputs_required:
  - workbook
inputs_optional:
  - previous briefing of the same template

truth_source: workbook cells

story_beats:
  - headline KPI
  - versus target if a target cell exists
  - movers (largest deltas vs previous file if present)
  - risks / asks only from a dedicated sheet or labeled rows

visual_grammar:
  - snapshot the real cell range to an image via headless render
  - do not ask an image model to redraw the chart

forbidden:
  - interpolating missing weeks
  - using last week's value when this week's cell is empty
  - "we should" unless a text cell says so

qa_checks:
  - every numeric token in the script matches the cited cell at generation time
  - empty required KPI cells fail the job instead of skipping quietly

outputs:
  - deck html
  - optional voiceover
  - cell_audit.csv

refresh_policy: upload new workbook to the template; diff cells; re-render dirty slides
