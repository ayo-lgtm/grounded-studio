# 07 — Job pipeline

```
upload → ingest → parse|transcribe → index sources → compile → qa → review → render → index script → published
```

Refresh inserts `diff` before compile.

Compile builds a context pack (transcript windows, cell pack, previous script, SKILL.md) and asks the local LLM for ScriptJSON at low temperature.

QA is Python with no model: citation pointers exist, times in range, numbers equal cells, glossary locks. Fail → one repair loop → else block render.

Render uses ffmpeg on the source video or HTML slides with real range snapshots. TTS is Piper/Kokoro per beat if original audio is not kept.

Jobs are idempotent on (briefing_id, type, input_hash, model_ids).
