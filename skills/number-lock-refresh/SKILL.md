# skill: number-lock-refresh
version: 1.0.0
offline: true
area: deck
job: Re-read every cited cell or block and fail the briefing if a published number no longer matches.

inputs_required:
  - published script
  - the workbook or document it cites
inputs_optional:
  - previous cell_audit.csv

truth_source: current cells and blocks versus the published tokens

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Parse numeric tokens from each beat.
  - Resolve each token to its citation. Compare to the live cell or to the number in the live block.
  - A match leaves the slide untouched.
  - A mismatch marks the slide dirty and blocks publish. Do not silently update the sentence.
  - An empty cell that used to hold a number fails closed. Do not substitute last week's value.
  - Write a diff of addr, old, new. A person accepts before any re-render.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - renderer: deck, but this skill does not restyle; it either keeps the parent html or blocks
  - layouts: unchanged

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - auto-rewriting the action title to fit the new number
  - interpolating a missing week
  - rounding to force a match

qa_checks:
  - every published numeric token is in the diff report as match or mismatch
  - mismatch count greater than zero blocks render
  - empty required cells fail
  - offline is true

outputs:
  - number-diff.csv
  - blocked or unchanged deck html

refresh_policy: this skill is the refresh check; run it before any weekly re-render

crafts:
  - citation-footer
  - slide-grammar
