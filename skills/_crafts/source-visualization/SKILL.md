# craft: source-visualization
version: 1.1.0
offline: true
used_by: weekly-ops-review, finance-wbr, half-year-business-review, executive-business-review, leadership-brief

job: Decide when the audience should see the original source instead of a reconstructed abstraction.

## Show the source when
- the exact table structure matters;
- finance users are expected to reconcile values visually;
- a metric is best understood in context with adjacent rows/columns;
- a recommendation depends on a specific document paragraph;
- the user explicitly asks to see the spreadsheet/document while it is explained.

## Workbook treatment
- capture only the smallest meaningful rectangular range;
- include row/column headers needed to understand it;
- highlight cited cells or rows;
- preserve number formats;
- never alter source values;
- freeze the view during the spoken claim;
- zoom only enough to make the cited evidence legible.

## Video sequence
1. orient: identify sheet/table and reporting period;
2. frame: show the relevant range;
3. focus: highlight the exact evidence;
4. explain: narrate the supported claim;
5. release: remove highlight before moving to the next region.

## Split-screen
Use source + commentary split only when both remain legible at 1080p.
Do not place a dense spreadsheet on one half of a 16:9 frame if the effective text becomes unreadable.

## Document/PDF treatment
Show the page/block when wording, legal language, policy text, or authored explanation matters.
Highlight only the cited sentence/paragraph.

## QA
- displayed range contains every cited cell used in the narration;
- highlight position matches the source coordinate;
- no neighboring confidential data is unnecessarily exposed;
- screenshot resolution is readable at final output size;
- source view and narration are synchronized.

## Runtime
Machine-read by `grounded.contracts`.
runtime_checks:
  - source-range-cited
