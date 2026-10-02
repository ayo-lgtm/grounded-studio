# craft: data-narration
version: 1.1.0
offline: true
used_by: weekly-ops-review, finance-wbr, half-year-business-review, executive-business-review

job: Turn accepted metrics and variances into concise spoken business language without overstating what the data proves.

## Sentence order
Prefer:
1. metric and current state;
2. comparison;
3. implication only if supported;
4. sourced explanation if available;
5. explicit ask/action if sourced.

Example pattern:
"Revenue was $12.4 million, $0.8 million above plan. The workbook attributes the variance to enterprise renewals."

## Spoken-number rules
- use the workbook's authored display when available;
- do not mix $12.4M on screen with "twelve million four hundred thousand" unless pronunciation policy requests it;
- say "percentage points" for differences between percentages;
- use basis points only for audiences that expect them;
- preserve negative signs semantically ("down", "below", "negative") rather than relying on a spoken minus symbol.

## Density
One spoken sentence should usually make one analytical claim.
Do not read entire tables row by row.
For a table, narrate the selection logic and the most decision-relevant entries while the complete cited table remains visible.

## Tone
Boardroom: concise, factual, no hype.
Finance: exact units, comparator named, period named when ambiguity is possible.
Operations: current state, variance, risk/ask.
Training: explanatory and paced.

## Prohibitions
Do not say:
- "obviously";
- "clearly" when evidence is contested;
- "strong performance", "weak performance", "healthy", "concerning", or similar evaluation without an explicit benchmark/policy;
- causal language without causal support.

## QA
- every numeric token maps to a claim object;
- every comparison names or visually establishes the comparator;
- every interpretation has evidence distinct from the arithmetic;
- narration does not omit an adverse variance solely for brevity.

## Runtime
Machine-read by `grounded.contracts`.
runtime_checks:
  - numbers-cited
  - no-unsourced-causal
  - model-text-reviewed
