# craft: chart-selection
version: 1.1.0
offline: true
used_by: weekly-ops-review, finance-wbr, half-year-business-review, executive-business-review, leadership-brief

job: Choose the simplest visual that answers the analytical question while preserving source truth.

## Selection grammar
- single KPI / status -> big number
- actual vs target -> paired values or bullet/progress form
- change over ordered time -> line
- discrete category comparison -> bar
- contribution to total change -> waterfall only when additive math is valid
- composition at one point -> 100% stacked bar when parts sum to a meaningful whole
- current vs prior across a small set -> grouped bar or compact table
- dense exact values -> table or source-range snapshot
- source workbook is itself important evidence -> source-range snapshot with highlights

## Prohibitions
- no pie/donut by default;
- no dual axes unless the skill explicitly allows it and units make the comparison defensible;
- no 3D charts;
- no decorative trend lines;
- no chart generated from uncited values;
- no "smooth" interpolation that changes the evidence;
- no sorting that destroys a meaningful sequence such as time.

## Data density
If viewers need exact values, prefer a table.
If the chart would contain more than 8 series or more than 20 category labels, simplify, facet, or show the source range instead.
Never shrink labels below the house readability floor merely to fit everything.

## Annotation
Annotations may state:
- cited value;
- derived variance with stored formula;
- sourced explanation.
They may not invent causes, forecasts, or recommendations.

## QA
- chart data and displayed values come from cited source ranges;
- units and axes are explicit;
- zero baseline is used for bars unless a documented exception applies;
- time axes remain chronological;
- highlights correspond to cited cells/series.

## Runtime
Machine-read by `grounded.contracts`.
runtime_checks:
  - single-unit-ranking
