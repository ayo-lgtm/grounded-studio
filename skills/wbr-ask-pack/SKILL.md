# skill: wbr-ask-pack
version: 1.0.0
offline: true
area: wbr
job: One ask slide per row on the ask sheet, with the owner only when that cell is filled.

inputs_required:
  - workbook ask sheet or an ask column labeled in the template
inputs_optional:
  - owner column
  - due cell

truth_source: ask rows

story_beats:
  - This skill specializes weekly-ops-review. It does not replace that file. Same truth rule: empty required KPI cells fail closed.
  - Plan the narrative before slides. Outline the beats this variant keeps, in WBR order: cover, headline, versus target, movers, risks, asks. Drop a beat the sheet does not support.
  - Action titles are corridor sentences built from header cells and cited values. The table on a slide is the cited cells, not a chart.
  - Footer is sheet!addr. house.py draws chrome. No style, color, font, css, theme, or background keys.
  - Do not interpolate a missing week. Do not reuse last week's number when this week's cell is empty.
  - Commentary sentences come only from text cells. A number in a sentence must equal a cited numeric cell.
  - Cover cites the week label.
  - One ask layout per non-empty ask cell, in row order.
  - The ask sentence is the cell text.
  - Owner and due date appear in the footer only when those cells are filled, next to the citation.
  - If the ask sheet is empty, fail into review only when the template marks asks as required; otherwise ship the cover and a statement that cites the empty sheet's header.

visual_grammar:
  - renderer: deck
  - chrome from house.py
  - family: boardroom or report
  - layouts limited to cover, big-number, versus-target, movers, risk, ask
  - layouts: cover, ask, statement

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - drafting an ask the cell does not contain
  - assigning an owner by role guess

qa_checks:
  - ask text equals the cell
  - owner text equals the owner cell or is absent
  - row order is preserved
  - offline is true

outputs:
  - deck html
  - ask-audit.csv

refresh_policy: rebuild rows that changed; stable ids per row key

crafts:
  - wbr-spine
  - slide-grammar
  - consulting-action-title
