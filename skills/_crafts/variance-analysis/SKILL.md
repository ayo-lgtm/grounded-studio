# craft: variance-analysis
version: 1.0.0
offline: true
used_by: weekly-ops-review, finance-wbr, half-year-business-review, executive-business-review

job: Compute and rank defensible changes without confusing arithmetic with explanation.

## Allowed comparisons
- current vs prior comparable period
- current vs target/plan
- current vs forecast
- YTD vs prior-year YTD
- H1 vs prior H1
- contribution to total change when additive structure is supported by the workbook

## Calculations
For each comparison persist:
- actual
- comparator
- absolute_delta = actual - comparator
- percent_delta only when comparator is non-zero and the metric is ratio-compatible
- percentage-point delta for rates/percentages
- basis-point delta only when requested or domain policy specifies it
- formula expression
- operand citations

## Materiality
Rank only after unit-aware normalization.
Use explicit materiality thresholds from workspace policy when present.
Without a threshold, describe size factually; do not call a movement "material", "significant", "strong", "weak", "good", or "bad" merely because it is large.

## Favorability
Do not infer that up is good or down is bad.
Favorability requires an explicit metric policy, target semantics, or sourced text.

## Causality
A variance is not a cause.
Never say "because", "driven by", "due to", "caused by", or equivalent unless:
- the workbook/document contains that causal explanation; or
- a mathematically valid contribution decomposition directly establishes the relationship.

Use "coincided with", "the largest observed movement was", or simple comparative language when causality is unsupported.

## Denominator safety
Do not calculate percentage change when the comparator is:
- zero;
- missing;
- non-comparable;
- a different scope or period.

## Ranking
When selecting movers, retain the complete candidate set and the ranking method.
Never suppress a large adverse or favorable variance solely to improve the story.

## QA
- every derived value stores its operands and formula;
- every operand is cited;
- percent vs percentage-point language is correct;
- sign is preserved;
- no causal wording without causal evidence;
- no cross-period comparison when scopes differ.
