# skill: launch-teaser-still-deck
version: 1.0.0
offline: true
area: deck
job: Build the stills-only slide companion to a launch teaser, one real frame per beat.

inputs_required:
  - recording frames or attached screenshots
  - launch document or transcript for the sentences
inputs_optional:
  - the launch-teaser-cut storyboard to keep the same order

truth_source: frames plus the sentence that cites them

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - Follow the teaser outline when a storyboard exists: hook, change, proof, closer.
  - Each slide is a statement. The sentence is spoken or copied from a cited block. The visual is the extracted PNG, stored as a file the deck references. Do not redraw the UI.
  - If house.py cannot place an image in the statement master, ship the sentence on the slide and attach the PNG in the beat visual as a cited still path. Do not invent a split master in this skill.
  - No price, date, or promise that is not in the doc.
  - Duration is a property of the video teaser, not of this deck. The deck is the leave-behind.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, statement, ask if the doc contains an ask
  - pitch family
  - still path must resolve to a local or MinIO object

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - a frame that is not from the recording or the attachments
  - generated product UI
  - cloud slide render

qa_checks:
  - every still path hashes to the extracted frame or the attachment
  - every sentence cites a block or a transcript span
  - proper nouns match the doc
  - offline is true

outputs:
  - deck html
  - stills used, copied into the briefing prefix
  - script json

refresh_policy: replace a slide when its frame or sentence source changes

crafts:
  - slide-grammar
  - frame-still
  - teaser-storyboard
