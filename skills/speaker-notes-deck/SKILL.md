# skill: speaker-notes-deck
version: 1.0.0
offline: true
area: deck
job: Keep the canvas to one cited idea and move delivery coaching into speaker notes.

inputs_required:
  - accepted deck script or a source document
inputs_optional:
  - a notes column or speaker script already in the document

truth_source: slide sentences from cited blocks; notes from a notes field in the source, or omitted

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - If the source has no notes field, speaker_notes.md stays empty for that slide. Do not coach from general knowledge.
  - Canvas body is one sentence. Extra sentences in the same block move to notes only when they are in the source, and they remain cited.
  - Notes never introduce a number that is not on the slide or in that block.
  - Render the deck through house.py. Notes are a sidecar markdown file, because house.py has no notes pane.
  - After render, check a local PNG of each slide for clipping. Overflow fails the slide.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: the parent layouts, otherwise cover and statement
  - one idea on the canvas
  - QA stills are local HTML screenshots, not a cloud render

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - writing presenter advice that is not in the source
  - moving a cited number off the slide into notes to make the slide cleaner
  - absolute positioning to fix overflow

qa_checks:
  - each slide has one body sentence on the canvas
  - notes text, if any, is a substring of the cited block
  - local stills show no clipped title or footer
  - no style keys
  - offline is true

outputs:
  - deck html
  - speaker_notes.md
  - qa-stills/

refresh_policy: rebuild notes when the source notes field changes; do not keep notes whose block was deleted

crafts:
  - slide-grammar
  - consulting-action-title
