# skill: wbr-commentary-lock
version: 1.0.0
offline: true
area: wbr
job: Allow narrative sentences only from commentary cells, and numbers only from numeric cells.

inputs_required:
  - workbook with a commentary column or sheet
inputs_optional:
  - the numeric slides from wbr-kpi-spine to attach notes to

truth_source: commentary text cells and the numeric cells they reference by address or by row

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - A commentary slide is a statement. The sentence is the commentary cell, copied.
  - If the commentary names a figure, that figure must equal the numeric cell on the same row. If it does not, fail the row.
  - Do not write connective tissue between comments.
  - Speaker notes may repeat the comment. They may not extend it.
  - Attach the comment to the matching KPI slide when the row key matches. Unmatched comments become their own statement slides.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - layouts: statement, plus the numeric layouts of any spine slides this skill is annotating

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - paraphrasing the comment
  - adding a cause the cell does not state
  - a comment with no cell

qa_checks:
  - statement body equals the commentary cell
  - figures inside a comment match the row's numeric cells or the row fails
  - offline is true

outputs:
  - deck html
  - speaker_notes.md
  - comment-audit.csv

refresh_policy: dirty a slide when its commentary cell or its numeric cells change

crafts:
  - wbr-spine
  - slide-grammar
  - consulting-action-title
  - citation-footer
