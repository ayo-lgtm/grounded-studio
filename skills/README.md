# Skills

Playbooks the compiler follows. v1 contracts are the eight skills in `docs/04-skills.md`. The expansion library adds offline, source-faithful skills for video, decks, capture, slideshows, and weekly business reviews.

`offline: true` on every skill. No public HTTP API, no cloud ASR, TTS, LLM, embeddings, or render. Local FFmpeg, `house.py`, faster-whisper, Piper or Kokoro, local OCR, and company MinIO, Postgres, and Redis only.

Chrome stays in `apps/engine/grounded/house.py`. A skill picks a story and a layout id.

## Video — recording editor

- [chaptered-demo-cut](chaptered-demo-cut/SKILL.md) — Cut a real screen recording into timeline-ordered chapters that follow the spoken task changes.
- [dead-air-trim](dead-air-trim/SKILL.md) — Remove measured silence from a real recording while keeping every spoken claim and its timestamps.
- [click-zoom-edit](click-zoom-edit/SKILL.md) — Punch in on a real click by cropping source pixels around a detected click box.
- [caption-burn-in](caption-burn-in/SKILL.md) — Burn captions that are the spoken line, timed to the local transcript, onto a real cut.
- [chapter-card-overlay](chapter-card-overlay/SKILL.md) — Insert a short title card before each chapter using the label read off the capture.
- [multi-clip-concat](multi-clip-concat/SKILL.md) — Join accepted clips in cited order into one recording-editor timeline.
- [highlight-reel-from-chapters](highlight-reel-from-chapters/SKILL.md) — Assemble a reel from chapters a human already marked keep, in their original order.
- [local-tts-duck-overlay](local-tts-duck-overlay/SKILL.md) — Lay a local Piper or Kokoro reading of an accepted script line under a ducked source bed.
- [side-by-side-before-after](side-by-side-before-after/SKILL.md) — Show two cited captures in one frame, before on the left and after on the right, using only their pixels.
- [accessibility-audio-description](accessibility-audio-description/SKILL.md) — Add an audio-description track that speaks only UI changes local OCR can see between cited frames.
- [launch-teaser-cut](launch-teaser-cut/SKILL.md) — Cut a 15 to 25 second teaser from recording stills only, rendered on the box.
- [filler-word-cut](filler-word-cut/SKILL.md) — Cut filler tokens listed in the local transcript and leave every other word in place.
- [poster-frame-pick](poster-frame-pick/SKILL.md) — Choose one cited source frame as the poster image for a briefing.
- [pace-hook-cut](pace-hook-cut/SKILL.md) — Score the opening of an accepted cut so a real spoken hook is audible inside the first three seconds.

## Presentation — deck renderer

- [kpi-spotlight-deck](kpi-spotlight-deck/SKILL.md) — Give each cited KPI its own big-number slide, with the action title taken from the cell label.
- [comparison-versus-deck](comparison-versus-deck/SKILL.md) — Compare two cited figures, or two cited statements, without adding a third number.
- [risk-and-ask-deck](risk-and-ask-deck/SKILL.md) — Build risk and ask slides only from rows or blocks the source already labels as risks or asks.
- [roadmap-timeline-deck](roadmap-timeline-deck/SKILL.md) — Turn dated items already in a document or sheet into ordered step slides.
- [decision-memo-deck](decision-memo-deck/SKILL.md) — Present the decision, the options the memo lists, and the chosen line, each cited.
- [stakeholder-variant-deck](stakeholder-variant-deck/SKILL.md) — Cut a shorter deck for an audience the source already names, using the same citations.
- [one-pager-summary-deck](one-pager-summary-deck/SKILL.md) — Produce a one-page brief and at most six slides whose sentences are copied from the source.
- [training-quiz-deck](training-quiz-deck/SKILL.md) — Turn questions and answers that already exist in a training doc or recording into step slides.
- [appendix-citation-pack](appendix-citation-pack/SKILL.md) — List every claim in a parent briefing as a statement slide whose body is the claim and whose footer is the citation.
- [number-lock-refresh](number-lock-refresh/SKILL.md) — Re-read every cited cell or block and fail the briefing if a published number no longer matches.
- [exec-narrative-deck](exec-narrative-deck/SKILL.md) — Turn a long memo into a sparse leadership deck plus an appendix of the blocks that did not fit.
- [launch-teaser-still-deck](launch-teaser-still-deck/SKILL.md) — Build the stills-only slide companion to a launch teaser, one real frame per beat.
- [speaker-notes-deck](speaker-notes-deck/SKILL.md) — Keep the canvas to one cited idea and move delivery coaching into speaker notes.

## Capture — ingest

- [screen-capture-ingest](screen-capture-ingest/SKILL.md) — Accept a local screen recording, hash it, and store it on company MinIO with geometry and duration.
- [mic-av-sync-align](mic-av-sync-align/SKILL.md) — Measure the offset between the mic track and the capture audio locally, then shift one track.
- [click-region-index](click-region-index/SKILL.md) — Index click coordinates and times from a local input log against the capture frame size.
- [ui-label-ocr-read](ui-label-ocr-read/SKILL.md) — Read on-screen text with local OCR and drop any label the detector cannot ground.
- [window-focus-segment](window-focus-segment/SKILL.md) — Split a capture into segments where the focused window title actually changes.
- [redaction-mask-pass](redaction-mask-pass/SKILL.md) — Mask denylisted strings found by local OCR before any later skill reads the picture.
- [multi-monitor-stitch](multi-monitor-stitch/SKILL.md) — Tile recorded displays into one frame using the geometry the capture wrote down.
- [cursor-trail-index](cursor-trail-index/SKILL.md) — Store cursor positions over time from the local capture stream or the local input log.
- [form-fill-step-extract](form-fill-step-extract/SKILL.md) — Extract one step per form field whose value local OCR sees change.
- [error-toast-capture](error-toast-capture/SKILL.md) — Clip the span where a toast or dialog is actually visible, with the text OCR read.
- [before-after-snapshot-pair](before-after-snapshot-pair/SKILL.md) — Pair two frames whose local pixel diff shows a real change, and record which is earlier.
- [allowlisted-path-replay](allowlisted-path-replay/SKILL.md) — Replay a path with Playwright only against hostnames listed in the on-disk internal allowlist.
- [clipboard-paste-detect](clipboard-paste-detect/SKILL.md) — Mark paste events from the local input log and describe only what local OCR sees after the paste.
- [transcript-window-index](transcript-window-index/SKILL.md) — Build word-timed transcript windows with local faster-whisper and store them next to the object.

## Slideshow — cited stills

- [still-sequence-slideshow](still-sequence-slideshow/SKILL.md) — Auto-advance through cited frames of a recording in timeline order.
- [chapter-still-advance](chapter-still-advance/SKILL.md) — Hold one cited frame per accepted chapter for the length of that chapter's speech.
- [before-after-still-show](before-after-still-show/SKILL.md) — Show the before still, then the after still, from an accepted snapshot pair.
- [launch-still-carousel](launch-still-carousel/SKILL.md) — Play a short carousel of launch screenshots that were attached or extracted from the recording.
- [sop-step-slideshow](sop-step-slideshow/SKILL.md) — Hold one cited frame per numbered SOP step, with the step sentence as the caption.
- [cited-frame-hold](cited-frame-hold/SKILL.md) — Hold a single cited frame for the spoken duration of its beat.

## WBR — weekly business review

- [wbr-kpi-spine](wbr-kpi-spine/SKILL.md) — Lay the canonical weekly business review order from a workbook: headline, target, movers, risks, asks.
- [wbr-executive](wbr-executive/SKILL.md) — Cut a short executive WBR: headline, target, top movers, one risk, one ask.
- [wbr-ops-deep-dive](wbr-ops-deep-dive/SKILL.md) — Give each named KPI section in the workbook its own cited slide, for operators who need the full pack.
- [wbr-region-roll-up](wbr-region-roll-up/SKILL.md) — One slide per region column the workbook already contains.
- [wbr-exception-only](wbr-exception-only/SKILL.md) — Show only rows the sheet flags as exceptions, and say so when the flag column is clean.
- [wbr-prior-week-delta](wbr-prior-week-delta/SKILL.md) — Show movers against the previous workbook only, with both cells cited.
- [wbr-ask-pack](wbr-ask-pack/SKILL.md) — One ask slide per row on the ask sheet, with the owner only when that cell is filled.
- [wbr-commentary-lock](wbr-commentary-lock/SKILL.md) — Allow narrative sentences only from commentary cells, and numbers only from numeric cells.

## Continuity and offline studio

Original offline playbooks. Not a hosted skill pack.

- [continuous-take-demo](continuous-take-demo/SKILL.md) — One take from a real capture. Every boundary keeps a survivor.
- [carry-boundary-verify](carry-boundary-verify/SKILL.md) — Fail when a boundary replaces the picture.
- [offline-quality-gate](offline-quality-gate/SKILL.md) — Pass, warn, or fail before a share link.
- [offline-refine-loop](offline-refine-loop/SKILL.md) — Cheapest local fix for a gate finding.
- [placement-formats-export](placement-formats-export/SKILL.md) — 16:9, 9:16, and 1:1 with a safe zone.
- [brand-kit-lock](brand-kit-lock/SKILL.md) — Palette and type from house.py.
- [storyboard-from-chapters](storyboard-from-chapters/SKILL.md) — Panels from cited chapters.
- [text-overlay-cards](text-overlay-cards/SKILL.md) — House labels on the source frame.
- [local-video-assembly](local-video-assembly/SKILL.md) — Concat the EDL locally.
- [caption-studio-local](caption-studio-local/SKILL.md) — Captions from local faster-whisper.
- [identity-consistency-lock](identity-consistency-lock/SKILL.md) — Screens the capture actually showed.
- [narration-room-mix](narration-room-mix/SKILL.md) — Local voice, loudness, duck, short room.

## Crafts

Reusable modules: [skills/_crafts](_crafts/). A craft does not ship a briefing alone.
