# skill: appendix-citation-pack
version: 1.0.0
offline: true
area: deck
job: List every claim in a parent briefing as a statement slide whose body is the claim and whose footer is the citation.

inputs_required:
  - accepted parent script
inputs_optional:
  - the parent source files for a live re-check of numbers

truth_source: parent beats and their citations

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - One statement slide per parent beat, in parent order. This pack may exceed 16 slides because it is an appendix, not a narrative. Record that exception in the script.
  - Title is the parent action title. Body is the parent sentence. Footer is the citation string.
  - Re-read numeric tokens against cells or blocks when the source file is still attached. Mismatch fails the pack.
  - Do not merge beats.
  - Cover slide states the parent title and the word Appendix only as a label in the eyebrow area that house.py already supports, using the parent title as the h1.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, statement
  - no new appendix chrome

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - editing a claim for length
  - dropping a beat that failed QA; the pack fails instead
  - adding commentary

qa_checks:
  - beat count equals parent beat count plus the cover
  - citation ids match the parent
  - numeric re-check passes or the job fails
  - offline is true

outputs:
  - deck html
  - citation-index.csv

refresh_policy: rebuild whenever the parent script changes

crafts:
  - slide-grammar
  - citation-footer
