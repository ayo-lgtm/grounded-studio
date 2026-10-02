# 17 — Implementation audit: production gaps and skill architecture

Audit date: 2026-10-02

## Executive finding

Grounded Studio has a credible grounded-rendering core, but the implementation is not yet aligned with the product promise that the Director can choose and invoke a rich library of production skills.

The most important architectural gap is that `skills/**/SKILL.md` is not loaded by the runtime. Skill behavior is currently duplicated and hard-coded in Python (`compile_sources.py`, `layouts.py`, `compile_deck.py`, and renderer conditionals). The markdown skill library is therefore documentation, not executable policy.

## P0 — blocks the intended product

### 1. Skill library is not runtime-addressable
There is no skill registry, parser, resolver, dependency graph, version pin, or execution context that loads `SKILL.md` contracts. The Director cannot discover or invoke crafts dynamically.

Required:
- machine-readable skill manifest;
- runtime skill resolver;
- craft dependencies;
- version pinning per generated briefing;
- skill/craft provenance in the compiled script;
- deterministic validation that a selected layout/renderer/output is permitted by the active skill contract.

### 2. Spreadsheet ingestion is not real spreadsheet ingestion
`compile_uploaded` expects a pre-shaped workbook JSON object. It does not parse arbitrary XLSX/CSV files into a semantic workbook model.

Required:
- XLSX and CSV parser;
- formulas and displayed-value capture;
- merged-cell handling;
- number formats;
- named ranges/tables;
- hidden rows/sheets policy;
- source-cell lineage;
- blank/error-cell semantics;
- workbook snapshots for visual display.

### 3. PDF ingestion is absent
The product promise includes PDF but current document compilation accepts DOCX or JSON block packs only.

Required:
- text-first PDF extraction;
- page/block coordinates;
- table extraction;
- page image fallback;
- stable page/block citations;
- fail-closed handling for scanned/garbled pages.

### 4. Current WBR logic is too narrow
The existing weekly review assumes a pre-authored pack containing `kpis`, `movers`, `risks`, and `asks`. It does not perform a defensible business-review analysis over a real workbook.

Required:
- metric discovery;
- time-grain detection;
- current/prior/plan/target semantics;
- absolute and percentage variance;
- denominator checks;
- materiality thresholds;
- contribution analysis;
- data-quality gates;
- executive storyline;
- source-region display when the workbook itself is the clearest evidence.

### 5. Rendering cannot yet show workbook evidence intelligently
Deck rendering can show KPI cards and a fixed movers table, but cannot render a selected workbook range, highlight cited cells, annotate a chart, or synchronize narration with a source table.

Required:
- workbook-range snapshot layout;
- highlighted-cell layout;
- chart-from-cited-series layout;
- source/table + commentary split layout;
- on-screen pan/zoom rules for data-heavy video.

## P1 — high-value quality gaps

- Script schema has no explicit skill dependencies, confidence, analysis method, formula lineage, source-range object, or visual-evidence contract.
- Numeric parser is US-centric and does not robustly distinguish percentages, basis points, ratios, dates, negatives in parentheses, accounting formats, or non-USD currencies.
- Derived claims are allowed but derivation formula and operands are not persisted.
- No semantic distinction between fact, derived metric, interpretation, risk, recommendation, and ask.
- No contradiction check across workbook/document/recording sources.
- No freshness or reporting-period consistency check.
- No visual QA for clipping, illegible tables, overcrowded charts, or source-highlight accuracy.
- TTS craft is intentionally local-only; deployment reality should be tested against available voices and pronunciation behavior.

## P2 — product maturity

- README maturity statement is stale.
- Skill catalog says not to add more skills until v1 works, but the target product now requires a broader modular craft library.
- No skill authoring tests, lint, or golden examples.
- No skill telemetry explaining which skill/craft produced a beat.
- No organization-specific policy layer for metric definitions, glossary terms, financial calendar, or approved wording.

## Recommended execution order

1. Make skills executable policy.
2. Add native XLSX/CSV + PDF ingestion.
3. Add source-range and chart evidence objects to the script schema.
4. Rebuild WBR/MBR/QBR/H1 review on the data-analysis crafts introduced in this branch.
5. Add workbook evidence layouts and synchronized narration.
6. Add visual/numeric QA and golden test packs.
7. Expand domain skills only after the registry and provenance are live.

## Acceptance standard

A finance user should be able to upload an ordinary workbook and ask for a WBR video or deck. The system should identify the reporting period, determine the important metrics and material variances, show the exact source range or cited chart when useful, narrate only supported conclusions, preserve every calculation's lineage, and refuse unsupported causal explanations.
