# 20 — Ask-me videos, courses and sharing

Record a demo once, add the knowledge base behind it, and share one link.
Everyone watches the same video and asks it questions. Each answer either
**shows them the moment** in the video or **quotes the source**. If the
answer is in neither, they get "That is not in this briefing."

## What a viewer gets

* **The video.** For a recording this is the edited film. For a document it
  is a narrated, chaptered walkthrough with captions (see below).
* **A chat box beside the video.** Every answer carries its source badge:
  *From the demo* (what was said), *On screen* (text read from the frame),
  *From the knowledge base* (a document block or page) or *From the
  workbook* (a cell or range).
* **Show me · m:ss.** Answers from the recording jump the film to that clip,
  play it and pause at its end. The jump goes through the edit decision list,
  so a cut film still lands on the right frame. Related clips are listed
  under *Watch it in the demo*. A refusal can still offer *Closest moments*.

## Matching questions to sources (`grounded/retrieval.py`)

Candidates come only from this briefing: script beats, speech segments,
on-screen text, knowledge-base blocks and workbook rows. Ranking is local and
deterministic:

* tokens are lower-cased, stop-worded and lightly stemmed;
* a curated synonym lexicon links everyday words ("bills" and "invoices",
  "log in" and "sign in", "teammate" and "member");
* BM25 scores the candidates. A candidate counts as an answer only when it
  covers enough of the question's concepts, so one shared word is not enough;
* optionally, a semantic embedder reranks and can rescue a paraphrase:
  `GROUNDED_EMBEDDING_PROVIDER=local-onnx` with a provisioned
  `GROUNDED_EMBEDDING_MODEL_DIR` (`model.onnx` and `tokenizer.json`, never
  downloaded), or Bedrock embeddings in `aws-private`.

When a chat model is enabled, it may only *choose* which retrieved passage
answers and *phrase* it. A phrasing that adds numbers, names or causes fails
`grounding.check_rewrite`, and the verbatim passage ships instead.

## Reading the screen (`grounded/screen_text.py`)

During `transcribe`, frames are sampled every `SCREEN_INTERVAL_S` seconds
(default 2), run through the selected image-text provider (local tesseract,
or Nova in `aws-private`) and deduplicated into timestamped spans. The spans
are stored as `transcript_segments` with `speaker='screen'`. Script
compilation ignores them, so narration never quotes OCR. Chat can cite them
("on screen at 0:42"). Screen reading runs when an image-text provider is selected:
`GROUNDED_IMAGE_TEXT_PROVIDER=local-ocr` (tesseract ships in the worker
image) or `bedrock`. The default is `none`, which turns it off.

## Documents to narrated video and courses

The `onboarding-guide` and `training-course` skills (and the aliases
`sop-training` and `training-quiz-deck`) compile a document into:

* **sections** from headings;
* **numbered steps** from numbered or bulleted lines and imperative
  sentences ("Collect…", "Request…");
* **notes** ("Know this") and **warnings** ("Watch out");
* **checkpoints** every three steps: "After …, what comes next?". The
  answer is the next step's own text, cited to both blocks, so nothing is
  invented.

`render` writes the deck and, when ffmpeg is present and `DECK_VIDEO` is
not `off`, `walkthrough.mp4`. Each beat becomes a 1080p frame in the house
style. Narration uses the local voice when `GROUNDED_TTS_PROVIDER=local`
(and fails the render if that voice is broken). Otherwise frames are held
for reading time. Checkpoints pause, then reveal the answer.
`edl.json` holds a chapter per beat, and `captions.vtt` holds the captions.

## Sharing inside the company login

`Share` on a briefing (editors only):

* **People.** Add work emails. Each one gets a `viewer` grant
  (`briefing_grants`).
* **Everyone signed in.** Sets `briefings.visibility = 'company'`, so any
  user authenticated by this deployment's SSO can watch.
* **Watch link.** `/watch/{id}` is a full-screen player with the chat box.
  It still requires sign-in, and there are no public or anonymous links.

Viewers can watch, read the script and its citations, and ask questions.
They can never upload, run jobs, re-share or download raw source files
(`/api/v1/assets/{id}/content` returns 403). Every share and unshare is
audited.
