# skill: wbr-executive
version: 1.0.0
offline: true
area: wbr
job: Cut a short executive WBR: headline, target, top movers, one risk, one ask.

inputs_required:
  - workbook
inputs_optional:
  - previous workbook
  - a text cell that ranks the single risk or ask to show

truth_source: workbook cells

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - Start from the wbr-kpi-spine outline and keep at most six slides.
  - Movers shows at most three rows, the largest absolute deltas among complete pairs. The ranking rule is recorded in the audit.
  - One risk and one ask. If several exist and no text cell picks one, fail into review with the list. Do not pick by severity you invent.
  - No deep-dive appendix in this skill. Point unused rows at wbr-ops-deep-dive.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - layouts used: cover, big-number, versus-target, movers, risk, ask, omitting those without cells

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a seventh slide
  - choosing a risk the sheet does not flag when more than one exists and none is marked primary

qa_checks:
  - slide count is at most 6
  - mover row count is at most 3
  - numbers match cells
  - offline is true

outputs:
  - deck html
  - cell_audit.csv
  - omitted-rows.csv

refresh_policy: same as the spine; the six-slide cap still applies

crafts:
  - wbr-spine
  - slide-grammar
  - consulting-action-title
