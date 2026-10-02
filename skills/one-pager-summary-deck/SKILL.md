# skill: one-pager-summary-deck
version: 1.0.0
offline: true
area: deck
job: Produce a one-page brief and at most six slides whose sentences are copied from the source.

inputs_required:
  - document or accepted parent script
inputs_optional:
  - workbook for figures already cited by the parent

truth_source: parent blocks or beats

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Pick at most five claims plus a cover. Each claim is one source sentence.
  - Prefer the source's own summary section when it exists. Do not summarize by rewriting.
  - Cap is six slides, which is tighter than the usual 6 to 16 range, because this skill is the short form.
  - The one-pager md is the same sentences in order, with citations under each.
  - Overflow material is listed as omitted ids, not squeezed onto a slide.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, statement, big-number only when a single cited figure is one of the five claims
  - center the statement; do not split

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a seventh slide
  - paraphrase that changes a number or a proper noun
  - a new concluding sentence

qa_checks:
  - slide count is at most 6
  - each body sentence equals a cited block or parent beat
  - one-pager sentences match the slides
  - offline is true

outputs:
  - deck html
  - one-pager.md
  - omitted-ids.json

refresh_policy: rebuild from the new source version; the cap still applies

crafts:
  - slide-grammar
  - citation-footer
