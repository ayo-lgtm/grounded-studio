# skill: wbr-ops-deep-dive
version: 1.0.0
offline: true
area: wbr
job: Give each named KPI section in the workbook its own cited slide, for operators who need the full pack.

inputs_required:
  - workbook whose section headers name the KPI groups
inputs_optional:
  - previous workbook

truth_source: workbook cells under those headers

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - One section, one slide, in sheet order. Layout is big-number when the section has a single value, or movers when it has a delta column.
  - Do not combine sections to save slides. If the pack would pass 16 slides, split into a second deck file rather than shrinking type, and say so in the audit.
  - Section title is the header cell.
  - Empty sections are listed as skipped, not shown as zero.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - section order follows the sheet, top to bottom

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - rolling a section up into a number the sheet does not contain
  - dropping a filled section to stay inside 16 slides without emitting the second deck

qa_checks:
  - every filled section appears on a slide or in the second deck
  - empty sections are in the skip list and not on slides
  - numbers match cells
  - offline is true

outputs:
  - deck html
  - optional deck-2.html
  - cell_audit.csv

refresh_policy: diff cells per section; dirty only the sections that changed

crafts:
  - wbr-spine
  - slide-grammar
  - citation-footer
