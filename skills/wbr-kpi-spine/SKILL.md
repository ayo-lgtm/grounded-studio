# skill: wbr-kpi-spine
version: 1.0.0
offline: true
area: wbr
job: Lay the canonical weekly business review order from a workbook: headline, target, movers, risks, asks.

inputs_required:
  - workbook matching the saved WBR template
inputs_optional:
  - previous workbook
  - template id

truth_source: workbook cells

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - Cover cites the week label cell. If that cell is empty, fail.
  - Headline is one big-number slide for the template's primary KPI.
  - Versus-target only when the target cell for that KPI is filled.
  - Movers lists the largest deltas versus the previous file, and only for rows where both cells exist. Cap the table at the rows that fit the house table without overflow.
  - Risk and ask slides only from sheets or columns labeled risk or ask.
  - Other WBR skills should follow this order and then narrow it.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - one idea per slide; movers is the one table

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a KPI the template does not name
  - smoothing a series
  - we should unless a text cell says so

qa_checks:
  - week label cell is non-empty
  - every numeric token matches its cell
  - empty primary KPI fails the job
  - mover rows cite both this week and last week
  - slide count is between 2 and 16
  - offline is true

outputs:
  - deck html
  - cell_audit.csv
  - script json

refresh_policy: new workbook on the template diffs cells and re-renders dirty slides

crafts:
  - wbr-spine
  - slide-grammar
  - consulting-action-title
  - citation-footer
