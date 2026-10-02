# skill: stakeholder-variant-deck
version: 1.0.0
offline: true
area: deck
job: Cut a shorter deck for an audience the source already names, using the same citations.

inputs_required:
  - accepted parent script
  - audience name that appears in the parent document or in the user hint and maps to a heading in the source
inputs_optional:
  - a heading in the doc that lists what that audience needs

truth_source: parent citations; this skill adds no sources

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Read the parent outline. Keep beats the source marks for that audience, plus the cover.
  - If the doc has no audience split, keep cover, decision or headline, and ask, and drop the rest only when those beats exist. Do not write new beats for the audience.
  - Duplicate the kept beats. Do not paraphrase. Layout ids stay.
  - Variant title appends the audience name only when that name is a source string.
  - Speaker notes may say which parent beats were omitted, citing their ids, so the omission is visible.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: whatever the parent beats already use, limited to the locked eight
  - same house chrome as the parent

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - new recommendations for the audience
  - simplifying a number
  - pulling beats from another briefing

qa_checks:
  - every variant citation id exists on the parent
  - numeric tokens are unchanged
  - omitted beats are listed in notes with parent ids
  - offline is true

outputs:
  - deck html
  - variant-manifest.json of kept and omitted beat ids

refresh_policy: if the parent re-renders, mark the variant stale and rebuild from the new parent

crafts:
  - slide-grammar
  - consulting-action-title
