# skill: roadmap-timeline-deck
version: 1.0.0
offline: true
area: deck
job: Turn dated items already in a document or sheet into ordered step slides.

inputs_required:
  - document or workbook whose rows include a date and a label
inputs_optional:
  - status column whose values are copied, not interpreted

truth_source: dated rows or blocks

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Sort by the date cell ascending. If a date cell is empty, leave that item out and list it in the audit as skipped.
  - One step slide per item. The sentence includes the date and the label copied from the cells.
  - house.py has no timeline master. Do not draw a line, arrow, or milestone graphic. The step layout is the sequence.
  - A status word appears only as the cell's text.
  - Cover cites the roadmap title in the source.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, step
  - no custom timeline CSS
  - dates are verbatim, including the source format

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - inventing a quarter, a ship date, or a dependency
  - grouping dates into phases the source does not name
  - a Gantt image

qa_checks:
  - step order matches ascending cited dates
  - every date token equals the cited cell or block
  - no slide lacks a citation
  - offline is true

outputs:
  - deck html
  - skipped-rows.csv

refresh_policy: re-sort when dates change; dropped rows leave the deck

crafts:
  - slide-grammar
  - citation-footer
