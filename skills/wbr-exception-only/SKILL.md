# skill: wbr-exception-only
version: 1.0.0
offline: true
area: wbr
job: Show only rows the sheet flags as exceptions, and say so when the flag column is clean.

inputs_required:
  - workbook with an exception flag column
inputs_optional:
  - threshold cell that the sheet uses; copy it, do not invent a threshold

truth_source: rows where the flag cell is the source's true value

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - Read the flag column. The true token is whatever the template documents, matched exactly.
  - One slide per flagged row. Layout is risk when the row is on the risk sheet, otherwise big-number or statement with the row's label and value.
  - If no row is flagged, the deck is a cover plus one statement whose sentence is built from the week label and the words the template uses for a clean week, and only if a template text cell contains that clean-week sentence. If it does not, the statement cites the flag column and says the flag column has zero true values, with that count computed from the column and shown in the audit.
  - Do not flag a row because the delta looks large.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - layouts: cover, statement, big-number, risk

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a private threshold
  - hiding a flagged row to keep the meeting short

qa_checks:
  - every data slide's row has a true flag
  - a clean week does not contain a data slide
  - the zero count matches the column
  - offline is true

outputs:
  - deck html
  - exception-audit.csv

refresh_policy: recompute flags from the new file; do not keep last week's exceptions

crafts:
  - wbr-spine
  - slide-grammar
  - citation-footer
