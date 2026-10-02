# skill: half-year-business-review
version: 1.0.0
job: Explain H1/H2 or first-half performance from one or more workbooks and supporting documents without losing period comparability.

inputs_required:
  - workbook
inputs_optional:
  - prior-year workbook
  - plan/forecast workbook
  - supporting memo/doc/pdf
  - metric policy

truth_source:
  numeric: workbook
  explanations: cited workbook text or supporting documents

crafts_required:
  - workbook-analysis
  - variance-analysis
  - chart-selection
  - source-visualization
  - data-narration
  - consulting-action-title
  - slide-grammar

## Period rules
H1 must resolve to a concrete date/fiscal range.
Never compare calendar H1 to fiscal H1 without an explicit mapping.
Prior-year H1 comparisons require equivalent scope and period length.
YTD and H1 are not interchangeable unless the reporting calendar establishes that they coincide.

## Story architecture
1. scope and reporting period
2. H1 headline outcomes
3. performance vs plan/target
4. H1 vs prior comparable H1
5. month/quarter progression inside H1
6. major contributors, with decomposition lineage
7. segment/product/region views only when source structure supports them
8. sourced risks and unresolved gaps
9. H2 outlook only if forecast/plan source exists
10. explicit asks/decisions only when sourced
11. appendix with reconciliation and calculation lineage

## Analytical discipline
Separate:
- actual results;
- arithmetic comparisons;
- sourced explanations;
- management interpretation;
- forecast/outlook.

Do not turn an H1 retrospective into an H2 forecast unless forecast data exists.
Do not annualize H1 by multiplying by two unless explicitly requested and clearly labeled as a mechanical annualization, not a forecast.

## Visual rules
Use trends for monthly/quarterly evolution, source-range snapshots for reconciliation-heavy finance tables, and waterfall only for valid additive bridges.

## Outputs
- H1/H2 briefing script
- deck
- optional narrated video
- source snapshots
- metric lineage audit
- calculation audit
