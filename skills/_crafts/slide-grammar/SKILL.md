# craft: slide-grammar
version: 1.0.0
source: adapted from stackblitz/bolt-slides + SlideSpeak slide-design-skill
used_by: leadership-brief, launch-announcement, weekly-ops-review, sop-training

job: Turn an accepted script into an HTML deck without inventing content.

rules:
  - Ground every slide in script beats and citations. No placeholders, fake names, or invented numbers.
  - 6 to 16 slides. One idea per slide.
  - Cover from document title. Close on an ask only if the source contains an ask.
  - Style tokens from workspace brand or visual-styles family. Do not reskin a starter deck.
  - Specialty layouts at most once, and only when content qualifies.
  - Center text-only slides. Split only when a real screenshot or table snapshot exists.
  - No third-party logos. No generated charts.
