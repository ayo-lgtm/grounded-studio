# skill: product-walkthrough
version: 1.0.0
job: Turn a real product recording into a chaptered walkthrough that stays faithful to the screen and the spoken words.

inputs_required:
  - recording
inputs_optional:
  - documents (help center, README)

truth_source: recording frames + transcript; documents only to clarify names already shown or spoken

story_beats:
  - hook (what this is for), only if the speaker said it or the doc states it
  - context (who uses it)
  - ordered steps following the recording timeline
  - recap
  - next action only if present in source

visual_grammar:
  - use the source video
  - zoom toward click or cursor if detected
  - never generate a fake UI
  - captions from the cleaned script

forbidden:
  - naming buttons, menus, or features not in the transcript or attached docs
  - inventing keyboard shortcuts
  - cinematic B-roll

qa_checks:
  - every beat has at least one recording citation with valid timestamps
  - step order matches increasing t_start_ms
  - product terms match glossary if present

outputs:
  - script json
  - chapters
  - mp4
  - vtt
  - guide.md

refresh_policy: replace dirty chapters when a new clip is attached; keep accepted beats whose citations still exist
