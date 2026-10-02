# skill: kpi-spotlight-deck
version: 1.0.0
offline: true
area: deck
job: Give each cited KPI its own big-number slide, with the action title taken from the cell label.

inputs_required:
  - workbook
inputs_optional:
  - previous workbook of the same template
  - a named KPI list that is a subset of existing headers

truth_source: workbook cells; a KPI with an empty value does not become a slide

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Cover uses the workbook title or file name, cited as the sheet.
  - One big-number slide per required KPI column that has a value. The figure is the cell. The label is the header cell.
  - Do not place two KPIs on one slide. house.py has no StatGrid master; do not invent one.
  - If a target cell exists for that KPI, the next slide is versus-target for that pair only.
  - Delta text is the computed difference of two cited cells, shown with the house delta line. Do not color it yourself; house.py marks the sign.
  - Stop at 16 slides. Extra KPIs move to appendix-citation-pack rather than shrinking type.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, big-number, versus-target
  - tabular figures; no sparklines
  - peer big-number slides use the same layout id

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - averaging weeks to fill an empty cell
  - a KPI the header row does not name
  - a chart image

qa_checks:
  - every numeric token equals the cited cell at generation time
  - empty required KPI fails the job
  - one KPI per big-number slide
  - title length fits the house cover or h1 measure; overflow fails
  - no beat carries a style key
  - slide count is between 1 and 16 including the cover
  - offline is true

outputs:
  - deck html
  - cell_audit.csv
  - speaker_notes.md only for notes that quote a text cell

refresh_policy: upload a new workbook; re-read cells; dirty any slide whose cited value changed

crafts:
  - slide-grammar
  - consulting-action-title
  - citation-footer
  - visual-styles
