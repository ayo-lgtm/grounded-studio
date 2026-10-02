# skill: finance-wbr
version: 1.0.0
job: Finance-grade weekly business review from an ordinary workbook, with exact lineage and source-first visuals.

inputs_required:
  - workbook
inputs_optional:
  - prior workbook
  - metric policy
  - reporting calendar
  - accompanying memo/doc
  - user emphasis

truth_source:
  primary: workbook cells, formulas, tables, and authored displays
  secondary: accompanying memo only for explanations, risks, and asks

crafts_required:
  - workbook-analysis
  - variance-analysis
  - chart-selection
  - source-visualization
  - data-narration
  - consulting-action-title
  - slide-grammar

## Director sequence
1. Validate workbook and reporting period.
2. Build metric inventory and resolve actual/prior/target semantics.
3. Run data-quality checks before analysis.
4. Compute allowed variances with operand lineage.
5. Rank review candidates using explicit materiality policy when available.
6. Build storyline: state -> variance -> drivers only if sourced -> risks -> asks.
7. Choose visual per beat. Prefer source-range evidence when reconciliation/context matters.
8. Produce deck and optional narrated video.
9. Run numeric, lineage, visual, and completeness QA.

## Default story
- cover: review period and scope
- executive headline: 1–3 decision-relevant facts, not a generic summary
- KPI performance: actual vs plan/target
- period movement: WoW and/or comparable prior period
- major contributors: only mathematically or textually supported
- source evidence: selected workbook ranges for complex sections
- risks: sourced only
- asks/decisions: sourced only
- appendix: complete metric/cell audit

## Selection rules
Do not automatically present every numeric cell.
Include a metric when it is:
- designated KPI;
- above an explicit materiality threshold;
- required by the saved template/policy;
- a contributor needed to explain a selected variance;
- a sourced risk/ask.

Completeness means all required/relevant selected data reaches the artifact; it does not mean reading the workbook cell-by-cell.

## Visual grammar
renderer: deck-and-video
preferred layouts:
- cover
- executive-headline
- big-number
- versus-target
- trend
- variance-table
- source-range
- source-range-highlight
- chart-with-source
- risk
- ask
- appendix-audit

## Refusals
Refuse or flag:
- missing comparator needed for requested variance;
- divide-by-zero percentage change;
- unexplained period mismatch;
- unsupported causal claims;
- KPI label collision;
- stale or mixed reporting periods;
- required cell errors.

## Outputs
- briefing script with skill/craft provenance
- deck
- optional narrated video
- workbook evidence snapshots
- cell_audit.csv
- calculation_audit.csv
- data_quality.json
