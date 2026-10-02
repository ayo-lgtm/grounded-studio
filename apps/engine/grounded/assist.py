"""Model assist for compiled scripts: polish wording, draft a summary.

The deterministic compiler has already produced a fully cited script. A
model (Amazon Nova in aws-private mode, or an internal model) may then:

``polish``   rephrase a beat. The rewrite must pass
             :func:`grounding.check_rewrite` against the beat it replaces.
``summary``  draft an executive-summary beat from existing beats only. Every
             sentence must name the beats it restates; every number in it
             must appear verbatim in those beats and match a cited claim
             (so derived values were already recomputed from cells); no
             cause, risk, recommendation, forecast, direction or entity may
             appear that those beats do not state.

Anything that fails is dropped and the deterministic text ships. After
assist, the full QA and contract gates run again; if they fail, the whole
assist is reverted. A provider error never triggers another provider.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from .grounding import CAUSAL, FORECAST, NEGATIVE, POSITIVE, RECOMMEND, RISK, _entities, _has, _words, check_rewrite, identifiers
from .numbers import close, parse_numbers
from .qa import DISPLAY_KEYS, validate_script

_POLISH_SYSTEM = (
    "You polish one sentence from a business briefing for a senior audience. Reply with JSON "
    "{\"text\": <sentence>}. Keep every number exactly as written. Do not add causes, risks, "
    "recommendations, forecasts, names or facts. Same meaning, clearer wording."
)

_SUMMARY_SYSTEM = (
    "You write an executive summary of a business briefing using ONLY the numbered beats given. "
    "Reply with JSON {\"sentences\": [{\"text\": <sentence>, \"beats\": [<beat numbers it restates>]}]}. "
    "At most three sentences. Copy numbers exactly as written in the beats. Never explain why "
    "something happened, never recommend, never forecast, never add anything not in the beats."
)

_TOKEN = re.compile(r"[$€£¥]?\d[\d,]*(?:\.\d+)?\s*[MmKk%]?")


def assist_script(script: dict[str, Any], provider: Any = None, cells: dict | None = None) -> dict[str, Any]:
    from .providers.base import ProviderError
    from .providers.registry import selection

    try:
        chosen = selection()
    except ProviderError:
        return script
    features = chosen.features & {"polish", "summary"}
    if not features or chosen.inference == "none":
        return script
    model = provider
    if model is None:
        from .providers.registry import inference_provider

        try:
            model = inference_provider(next(iter(sorted(features))))
        except ProviderError as exc:
            out = copy.deepcopy(script)
            out.setdefault("assist_notes", []).append(f"assist skipped: {exc}")
            return out
    if model is None:
        return script
    candidate = copy.deepcopy(script)
    notes: list[str] = []
    if "polish" in features:
        notes += polish_beats(candidate, model)
    if "summary" in features:
        notes += add_summary(candidate, model)
    errors = validate_script(candidate, duration_ms=candidate.get("source_duration_ms"), cells=cells)
    errors += _contract_errors(candidate)
    if errors:
        reverted = copy.deepcopy(script)
        reverted.setdefault("assist_notes", []).append(f"assist reverted: {errors[0]}")
        return reverted
    candidate["assist_notes"] = notes
    candidate["providers"] = {
        **(candidate.get("providers") or {}),
        "assist": f"{getattr(model, 'name', 'model')}:{getattr(model, 'model_id', '')}",
        "assist_features": sorted(features),
    }
    return candidate


def _contract_errors(script: dict[str, Any]) -> list[str]:
    from .contracts import run_checks, runtime_for
    from .skill_registry import SkillRegistryError, resolve_skill

    try:
        skill, crafts = resolve_skill(str(script.get("skill_id") or ""))
    except SkillRegistryError:
        return []
    return run_checks(script, runtime_for(skill, crafts), None)


def _complete_json(model: Any, system: str, prompt: str, max_tokens: int = 600) -> dict[str, Any] | None:
    from .providers.base import ProviderError

    try:
        result = model.complete(system, prompt, max_tokens=max_tokens)
        raw = result.text if hasattr(result, "text") else str(result)
        start, end = raw.find("{"), raw.rfind("}")
        parsed = json.loads(raw[start : end + 1]) if start >= 0 and end > start else None
    except (ProviderError, ValueError, AttributeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _surfaces(beat: dict[str, Any]) -> list[str]:
    slots = beat.get("slots") or {}
    return [str(slots[key]) for key in ("actual", "target") if isinstance(slots.get(key), str)]


def polish_beats(script: dict[str, Any], model: Any) -> list[str]:
    notes = []
    for beat in script.get("beats") or []:
        if beat.get("layout") in {"cover", "source-range", "movers"}:
            continue
        old = str(beat.get("text") or "")
        parsed = _complete_json(model, _POLISH_SYSTEM, f'Sentence: "{old}"')
        new = str((parsed or {}).get("text") or "").strip()
        verdict = check_rewrite(old, new, _surfaces(beat)) if new else None
        if verdict is None or not verdict.ok:
            notes.append(f"beat {beat.get('ord')} kept verbatim ({verdict.reason if verdict else 'no reply'})")
            continue
        beat["text"] = new
        beat.setdefault("assist", []).append(
            {"op": "polish", "provider": getattr(model, "name", "model"), "model_id": getattr(model, "model_id", ""), "source_text": old}
        )
        notes.append(f"beat {beat.get('ord')} polished")
    return notes


def _beat_text(beat: dict[str, Any]) -> str:
    parts = [str(beat.get("text") or "")]
    slots = beat.get("slots") or {}
    for key in DISPLAY_KEYS:
        if isinstance(slots.get(key), str):
            parts.append(slots[key])
    return " ".join(parts)


def check_summary_sentence(text: str, sources: list[dict[str, Any]]) -> str | None:
    """None if ``text`` only restates ``sources`` (beats); else the reason."""
    if not text.strip():
        return "empty sentence"
    if not sources:
        return "sentence names no beats"
    source_text = " ".join(_beat_text(beat) for beat in sources)
    claims = [claim for beat in sources for claim in beat.get("claims") or []]
    for token in _TOKEN.findall(text):
        surface = token.strip()
        if surface not in source_text:
            return f"number {surface!r} is not written that way in the cited beats"
    for number in parse_numbers(text):
        if not any(close(number, float(claim["value"])) for claim in claims):
            return f"number {number:g} has no cited claim"
    novel_ids = identifiers(text) - identifiers(source_text)
    if novel_ids:
        return f"identifier {sorted(novel_ids)[0]!r} is not in the cited beats"
    for label, phrases in (("causal claim", CAUSAL), ("recommendation", RECOMMEND), ("risk", RISK), ("forecast", FORECAST)):
        added = _has(phrases, text) - _has(phrases, source_text)
        if added:
            return f"unsupported {label} ({sorted(added)[0]})"
    words, src = _words(text), _words(source_text)
    if (words & set(POSITIVE)) - src or (words & set(NEGATIVE)) - src:
        return "direction not stated in the cited beats"
    novel = _entities(text) - src
    if novel:
        return f"unsupported entity ({sorted(novel)[0]})"
    return None


def add_summary(script: dict[str, Any], model: Any) -> list[str]:
    from .contracts import runtime_for
    from .skill_registry import SkillRegistryError, resolve_skill

    try:
        skill, crafts = resolve_skill(str(script.get("skill_id") or ""))
        runtime = runtime_for(skill, crafts)
    except SkillRegistryError:
        return ["summary skipped: unknown skill"]
    if "statement" not in runtime.layouts:
        return ["summary skipped: the skill has no statement layout"]
    beats = list(script.get("beats") or [])
    if runtime.max_slides and len(beats) + 1 > runtime.max_slides:
        return ["summary skipped: slide cap reached"]
    numbered = "\n".join(
        f"[{beat.get('ord')}] {_beat_text(beat)}" for beat in beats if beat.get("layout") not in {"cover", "source-range"}
    )
    parsed = _complete_json(model, _SUMMARY_SYSTEM, numbered, max_tokens=800)
    sentences = (parsed or {}).get("sentences") or []
    by_ord = {beat.get("ord"): beat for beat in beats}
    kept: list[str] = []
    cites: list[dict[str, Any]] = []
    claims: list[dict[str, Any]] = []
    notes: list[str] = []
    for item in sentences[:3]:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        refs = [by_ord[o] for o in item.get("beats") or [] if o in by_ord and by_ord[o].get("layout") != "cover"]
        problem = check_summary_sentence(text, refs)
        if problem:
            notes.append(f"summary sentence dropped ({problem})")
            continue
        kept.append(text)
        for beat in refs:
            for cite in beat.get("citations") or []:
                if cite not in cites:
                    cites.append(dict(cite))
            for claim in beat.get("claims") or []:
                if any(close(n, float(claim["value"])) for n in parse_numbers(text)) and claim not in claims:
                    claims.append(dict(claim))
    if not kept:
        return notes + ["summary skipped: no sentence passed grounding"]
    summary = {
        "kind": "summary",
        "layout": "statement",
        "text": " ".join(kept),
        "slots": {"eyebrow": "Executive summary"},
        "claims": claims,
        "citations": cites,
        "assist": [
            {
                "op": "summary",
                "provider": getattr(model, "name", "model"),
                "model_id": getattr(model, "model_id", ""),
                "source_text": " ".join(_beat_text(b) for b in beats if b.get("layout") != "cover"),
            }
        ],
    }
    insert_at = 1 if beats and beats[0].get("layout") == "cover" else 0
    beats.insert(insert_at, summary)
    for index, beat in enumerate(beats, start=1):
        beat["ord"] = index
    script["beats"] = beats
    return notes + ["summary added"]
