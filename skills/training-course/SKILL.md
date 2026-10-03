# skill: training-course
version: 1.0.0
offline: true
job: Turn a procedure, how-to or tutorial document into a narrated training video with numbered steps and checkpoints.

inputs_required:
  - document
inputs_optional:
  - presentation
  - screenshots
  - a recorded walkthrough of the tools
  - previous version of the course

truth_source: the uploaded documents only; every sentence is quoted from a block

crafts_required:
  - data-narration
  - slide-grammar

story_beats:
  - cover: the course title from the document
  - sections in document order, named by the document's headings
  - numbered steps for every instruction ("Request laptop access on day one.")
  - "Know this" notes for policies and facts
  - checkpoints every three steps: "after X, what comes next?" answered by the next step, verbatim
  - asks and watch-outs copied from the document

visual_grammar:
  - renderer: deck, plus a narrated video (local voice) with chapters and captions
  - layouts: cover, step, statement, ask
  - chrome comes from house.py

forbidden:
  - any external HTTP API, SaaS endpoint, cloud ASR, cloud TTS, cloud LLM, cloud embeddings, or cloud render; no public internet egress
  - inventing steps, tips, policies, dates or numbers that the documents do not state
  - reordering steps

outputs:
  - deck html
  - narrated training video (mp4), captions, chapters
  - grounded chat over the documents

## Runtime
Machine-read by `grounded.contracts`; unknown check ids fail the compile.
runtime_compiler: document-deck
runtime_accepts:
  - document
  - presentation
  - image
runtime_requires_any:
  - document
  - presentation
  - image
runtime_layouts:
  - cover
  - step
  - statement
  - ask
  - risk
runtime_checks:
  - citations-present
  - numbers-cited
