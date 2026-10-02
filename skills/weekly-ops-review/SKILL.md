# skill: weekly-ops-review
version: 2.1.0
offline: true
job: Recurring operations/business review from a workbook, with cited metrics, defensible variance analysis, and source-faithful visuals.

inputs_required:
  - workbook
inputs_optional:
  - previous comparable workbook
  - saved metric/template policy
  - supporting memo
  - user emphasis

truth_source:
  numeric: workbook cells/formulas
  explanations: labeled workbook text or supporting memo

crafts_required:
  - workbook-analysis
  - variance-analysis
  - chart-selection
  - source-visualization
  - data-narration
  - consulting-action-title
  - slide-grammar

## Director sequence
1. Resolve reporting period and metric identities.
2. Run data-quality gates.
3. Identify required KPIs from saved template/policy.
4. Compute current-vs-prior and actual-vs-target comparisons only when comparable.
5. Select decision-relevant movers using explicit materiality when available.
6. Separate arithmetic movement from sourced explanation.
7. Choose the simplest visual; show the workbook range when reconciliation/context matters.
8. Include sourced risks and asks.
9. Run numeric, lineage, period, completeness, and visual QA.

## Story beats
- cover / reporting period
- executive headline
- required KPI status
- versus target/plan when present
- largest defensible movers
- source-range evidence for dense tables
- risks from sourced text
- asks from sourced text
- appendix audit

## Completeness
Every required KPI and every selected mover must appear with lineage.
Do not interpret completeness as reading every workbook cell.

## Forbidden
- any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render; no public internet egress
- interpolating missing weeks
- silently carrying forward prior values
- percentage change from a zero denominator
- treating up as good or down as bad without metric policy
- causal wording without sourced explanation or valid contribution math
- hiding an adverse variance to shorten the story
- invented recommendations

## QA
- every numeric token maps to a cited or derived claim;
- every derived claim stores formula and operand citations;
- empty required KPI cells fail closed;
- reporting periods are comparable;
- source snapshots highlight the cited cells;
- displayed workbook values preserve authored number formats.

outputs:
  - deck
  - optional narrated video
  - source snapshots
  - cell_audit.csv
  - calculation_audit.csv
  - data_quality.json

refresh_policy: upload the new comparable workbook; re-run semantic mapping and variance analysis; preserve metric identity only when the saved template/policy still resolves unambiguously.

## Runtime
Machine-read by `grounded.contracts`; unknown check ids fail the compile.
runtime_compiler: workbook-deck
runtime_accepts:
  - workbook
  - document
  - presentation
runtime_requires_any:
  - workbook
runtime_layouts:
  - cover
  - big-number
  - versus-target
  - movers
  - source-range
  - risk
  - ask
runtime_max_slides: 24
runtime_checks:
  - citations-present
  - numbers-cited
  - period-cited
