# craft: workbook-analysis
version: 1.1.0
offline: true
used_by: weekly-ops-review, finance-wbr, half-year-business-review, executive-business-review

job: Convert a real workbook into a source-faithful semantic metric model before any story is written.

## Required outputs
- workbook inventory: sheets, tables, named ranges, visible/hidden state
- reporting-period candidates
- metric candidates with label, unit, grain, current value, prior value, target/plan when present
- source lineage for every value: sheet, address/range, formula if any, displayed value, raw value, number format
- data-quality findings

## Discovery rules
1. Prefer explicit tables, named ranges, headers, labels, and repeated period columns over positional guessing.
2. Detect common period headers: week, month, quarter, H1/H2, YTD, FY, prior year, plan, target, forecast.
3. Keep raw value and displayed value separately. Never reconstruct a displayed value from raw data when the workbook already authored the display.
4. Preserve formulas. A formula result is a sourced value, but the formula text and precedents must remain inspectable.
5. Do not treat totals, subtotals, percentages, counts, rates, currency, and ratios as interchangeable.
6. Hidden rows/sheets may be read for lineage but must be marked hidden; do not surface them to users unless policy permits.
7. Merged cells inherit their visible label only within the merged region.
8. Blank, error, #N/A, #DIV/0!, and formula-empty are distinct states.

## Metric identity
A metric is not just a number. Store:
- canonical label
- source label
- unit/currency
- aggregation type
- time grain
- period
- scope/segment
- actual/target/plan/forecast/prior semantic role
- source range
- formula lineage
- authored display

## Fail closed
Do not guess:
- which of two plausible date columns is "current";
- whether 0 means missing;
- whether a percentage is 0.12 or 12%;
- whether a favorable direction is higher or lower;
- whether two similarly named metrics are equivalent.

When ambiguous, emit an ambiguity object for the Director instead of silently choosing.

## QA
- every metric value resolves back to a source cell/range;
- display and raw value are both retained;
- formulas are never replaced with invented calculations;
- reporting periods are internally consistent;
- no narrative generation begins while required metric identity is ambiguous.

## Runtime
Machine-read by `grounded.contracts`.
runtime_checks:
  - cell-exists
  - source-range-cited
