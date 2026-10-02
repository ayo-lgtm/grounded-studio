# skill: risk-and-ask-deck
version: 1.0.0
offline: true
area: deck
job: Build risk and ask slides only from rows or blocks the source already labels as risks or asks.

inputs_required:
  - workbook with a risk or ask sheet, or a document with those headings
inputs_optional:
  - owner column
  - date column

truth_source: labeled risk and ask entries

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Cover cites the document title or the sheet name.
  - One risk slide per risk row or block. Layout is risk. Body is the source sentence.
  - One ask slide per ask row or block. Layout is ask. The ask sentence is copied.
  - Owner and date appear only when those cells are filled, in the footer beside the citation.
  - Omit the section when the sheet is empty. Do not add a placeholder risk.
  - Do not upgrade a risk into an ask.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, risk, ask
  - risk eyebrow is the house risk style; the skill does not recolor it

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a mitigation that is not written in the source
  - assigning an owner who is not in a cell or block
  - sorting risks by a severity the sheet does not contain

qa_checks:
  - every slide cites a row or block tagged risk or ask in the source
  - body text is a copy of that source text
  - empty ask sheet produces no ask slide
  - offline is true

outputs:
  - deck html
  - speaker_notes.md if the source has a note column

refresh_policy: recompile when the risk or ask sheet changes; keep slide ids stable per source row id

crafts:
  - slide-grammar
  - consulting-action-title
  - citation-footer
