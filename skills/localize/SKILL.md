# skill: localize
version: 1.0.0
job: Create a language sibling of a published briefing without changing facts.

inputs_required:
  - published briefing
  - target_language (from workspace allowlist)

truth_source: parent citations; do not add sources

story_beats: inherit parent beats in the same order

visual_grammar: reuse parent video frames or slides; replace captions and TTS only

forbidden:
  - changing numbers
  - changing product names that are in the glossary
  - adding beats

qa_checks:
  - citation ids identical to parent
  - numeric tokens identical
  - glossary terms preserved

outputs:
  - translated script
  - vtt
  - tts track
  - sibling briefing row (parent_id set)

refresh_policy: if parent re-renders, mark sibling stale
