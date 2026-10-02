# skill: training-quiz-deck
version: 1.0.0
offline: true
area: deck
job: Turn questions and answers that already exist in a training doc or recording into step slides.

inputs_required:
  - document or recording transcript that contains question and answer pairs
inputs_optional:
  - SOP steps from sop-training as the lesson before the questions

truth_source: the question and answer text in the source

story_beats:
  - Read the sources and list candidate claims. Drop any claim that has no citation.
  - Write a compact outline before slides: audience, purpose, and the beat order. One idea per slide.
  - Action title is a corridor sentence built only from cited tokens. Bad titles such as Overview or Key takeaways are allowed only when that heading is in the source.
  - Evidence is one to three bullets or one table of cited cells. Coaching the speaker wrote goes to speaker notes, not the canvas.
  - Footer is the citation: sheet!addr, block_id, or recording t_start_ms–t_end_ms. house.py draws it.
  - Map each beat to a locked layout id. Do not emit style, color, font, css, theme, or background.
  - A pair counts only when the source marks a question and its answer, or the speaker asks and then answers.
  - One step slide per question. The canvas shows the question. The answer goes to speaker notes and to an answer key file, still cited.
  - Do not write a new question to test a step that had none.
  - If the source has fewer than one pair, fail. An empty quiz is not a deck of tips.
  - Lesson context, when present, is a statement slide quoting the purpose line, before the questions.

visual_grammar:
  - renderer: deck
  - chrome comes from house.py; this skill picks layout ids only
  - family comes from visual-styles via skill id, unless the workspace brand overrides
  - no third-party logos and no generated charts; a table is the cited cells
  - layouts: cover, statement, step
  - teaching family
  - no scored widget, timer, or confetti

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render
  - public internet egress of any kind; company MinIO, Postgres, and Redis are allowed only when they are self-hosted on localhost or the company network and never leave that network
  - OpenAI, Anthropic, ElevenLabs, Veo, Runway, HeyGen, Slides.com, Google Slides API, Higgsfield, cloud Remotion, or any third-party video or slide service
  - generative B-roll, invented UI, invented numbers, avatars, stock footage, or cloud music
  - invented distractors
  - marking an answer correct when the source does not
  - pulling questions from another course

qa_checks:
  - every question string equals the cited source text
  - the answer key cites the same pair
  - no question lacks an answer in the source
  - offline is true

outputs:
  - deck html
  - answer-key.md
  - speaker_notes.md

refresh_policy: rebuild when the source pairs change; keep pair ids stable when the question text is unchanged

crafts:
  - slide-grammar
  - citation-footer
