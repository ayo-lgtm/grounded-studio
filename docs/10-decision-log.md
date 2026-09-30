# 10 — Decision log

## D1. In-house only
Employee files do not go to public LLM/TTS/video APIs. Local Whisper, local LLM, local embeddings, local TTS.

## D2. Recording over codebase
Demos start from a human recording. `/brag` is not v1.

## D3. Show real pixels and real cells
No generated UI. No generated Excel.

## D4. Skills not one model
Eight v1 skills. Router suggests. User confirms. QA is deterministic Python.

## D5. Script is the linguistic source of truth
MP4 and deck are projections.

## D6. Human accept before publish
Compile can fail closed.

## D7. Chat refuses
No web. No other briefings in context.

## D8. Study OpenMontage / Diffusion / Bolt Slides
Do not vendor AGPL OpenMontage. Render with ffmpeg + HTML slides first.

## D9. Two renderers, one house style
`product-walkthrough`, `sop-training`, and `feature-delta` share the recording editor.
`weekly-ops-review`, `leadership-brief`, and `launch-announcement` share locked slide masters.
Tokens live in `apps/engine/grounded/house.py`. A script that carries `style`, `color`, or `font` fails QA.

## D10. The model fills slots
Action titles for a workbook are sentences over cited cells. Document beats copy the source sentence.
Empty required KPIs fail the compile. A localized line whose numbers differ fails the compile.
Chat quotes a beat or refuses.
