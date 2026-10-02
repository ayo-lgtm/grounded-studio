# skill: wbr-region-roll-up
version: 1.0.0
offline: true
area: wbr
job: One slide per region column the workbook already contains.

inputs_required:
  - workbook with a region header row or a region column
inputs_optional:
  - a total column, cited separately and never recomputed if the cell exists

truth_source: region cells

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - Read region names from the header. One big-number or versus-target slide per region that has a value.
  - If a total cell exists, it is its own slide and is not the sum you calculate, even if you also show the parts.
  - A region with an empty value is skipped and listed. It is not zero.
  - Order is the sheet's column order.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - peer slides share one layout id

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - adding a region that is not a header
  - allocating a total across regions
  - a map

qa_checks:
  - region labels equal header cells
  - each figure cites that region cell
  - total slide, if present, cites the total cell and not a formula the skill ran
  - offline is true

outputs:
  - deck html
  - cell_audit.csv

refresh_policy: re-render regions whose cells changed

crafts:
  - wbr-spine
  - slide-grammar
  - citation-footer
