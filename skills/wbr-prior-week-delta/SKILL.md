# skill: wbr-prior-week-delta
version: 1.0.0
offline: true
area: wbr
job: Show movers against the previous workbook only, with both cells cited.

inputs_required:
  - this week's workbook
  - previous week's workbook of the same template
inputs_optional:
  - a row inclusion list that is a column in the template

truth_source: paired cells in the two workbooks

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - Align rows by the template's key column, not by position, unless the template has no key and documents positional alignment.
  - A mover exists when both cells are filled. Delta is this minus previous, and both addresses are cited.
  - Sort by absolute delta descending for the movers table. Record the sort.
  - A row missing on one side is listed in the audit and omitted. It is not zero.
  - No commentary beyond a text cell on that row.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - layout: cover and movers; big-number only for the single largest mover if the template names a headline KPI

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - pairing rows by similar names
  - using a week older than the previous file
  - percent change when the previous cell is zero; omit the percent and keep the raw delta only if both cells exist and the template has a delta column, otherwise show the two values without a percent

qa_checks:
  - every mover cites two addresses
  - delta equals the difference of those cells
  - unpaired rows are in the audit and not on the slide
  - offline is true

outputs:
  - deck html
  - pair-audit.csv

refresh_policy: a new current or previous file rebuilds the pairs

crafts:
  - wbr-spine
  - slide-grammar
  - citation-footer
