# skill: exec-narrative-deck
version: 1.0.0
offline: true
area: deck
job: Turn a long memo into a sparse leadership deck plus an appendix of the blocks that did not fit.

inputs_required:
  - document longer than the sparse deck can hold
inputs_optional:
  - workbook cited by the memo

truth_source: document blocks

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Outline the corridor story: situation, recommendation or ask, evidence, risks, next step. Omit a beat the memo lacks.
  - Select the fewest blocks that carry those beats. Cap the narrative at 16 slides.
  - Each slide sentence is the source sentence, not a compression that drops a number.
  - Blocks not used go to the appendix list with block ids. They are not deleted from the briefing.
  - This is the v1.5 exec-narrative contract under the id exec-narrative-deck. It does not replace leadership-brief.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, statement, risk, ask
  - big-number only when the memo cites one figure and the slide is that figure
  - consulting or boardroom family

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a new recommendation
  - leaving a cited number out of a sentence that contained it, in order to shorten the slide
  - benchmarks absent from the memo

qa_checks:
  - every narrative slide cites a block_id
  - numbers on slides equal numbers in those blocks
  - appendix ids are the complement of the used blocks
  - offline is true

outputs:
  - deck html
  - appendix.md
  - optional local voiceover of the slide sentences

refresh_policy: recompile on a new doc version; diff block ids; dirty slides whose blocks changed

crafts:
  - slide-grammar
  - consulting-action-title
  - citation-footer
  - tts-narration
