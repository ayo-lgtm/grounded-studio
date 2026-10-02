# skill: decision-memo-deck
version: 1.0.0
offline: true
area: deck
job: Present the decision, the options the memo lists, and the chosen line, each cited.

inputs_required:
  - decision document
inputs_optional:
  - workbook of cited costs attached to the same briefing

truth_source: document blocks; numbers only from cited blocks or cells

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Outline: situation, options, decision, risks, next step. Drop any heading the memo does not contain.
  - Options are statement slides, one option per block, in memo order. Do not rank them.
  - The decision slide is a statement whose sentence is the memo's decision sentence, or an ask slide if the memo phrases it as an ask.
  - A cost on an option must cite a block or a cell. No cost, no figure.
  - Close on the next step only when the memo states one.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, statement, risk, ask
  - consulting family: action title, evidence, source footer

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - recommending an option the memo does not choose
  - adding an option for balance
  - changing we are considering into we will

qa_checks:
  - decision sentence equals the cited block
  - option count equals the option blocks
  - numbers match cited blocks or cells
  - offline is true

outputs:
  - deck html
  - one-pager md of the same sentences
  - block_audit.csv

refresh_policy: recompile from a new doc version; diff block ids

crafts:
  - slide-grammar
  - consulting-action-title
  - citation-footer
