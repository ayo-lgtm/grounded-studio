# skill: comparison-versus-deck
version: 1.0.0
offline: true
area: deck
job: Compare two cited figures, or two cited statements, without adding a third number.

inputs_required:
  - workbook or document that contains both sides of the comparison
inputs_optional:
  - a label row that names the two columns

truth_source: the two cited cells or the two cited blocks

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Identify the pair from column headers or from two doc headings. If a third option is in the source, it gets its own later slide or it is omitted, never folded into the pair.
  - Numeric pair uses versus-target. Left and right labels are the header cells.
  - Prose pair uses two statement slides, one side each, in the source order. Do not use a split layout unless both sides are text; house.py has no image split.
  - A recommendation slide exists only when a cell or block states the choice.
  - Action title states the comparison using the two labels. It does not say which side wins unless the source says so.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, versus-target, statement
  - table snapshot only when the pair is a cited row range, rendered as the house table

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - benchmarks that are not in the file
  - percent change when either cell is empty
  - icons that imply a winner

qa_checks:
  - each versus-target slide cites exactly two numeric cells
  - labels match header text
  - no numeric token beyond those cells and a delta of those two cells
  - offline is true

outputs:
  - deck html
  - cell_audit.csv or block_audit.csv

refresh_policy: recompile when either cited cell or block changes

crafts:
  - slide-grammar
  - consulting-action-title
  - citation-footer
