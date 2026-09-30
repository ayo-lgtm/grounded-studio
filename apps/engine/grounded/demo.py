"""Run every v1 skill on fixtures and write a review folder."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Callable

from .chat import answer
from .compile_deck import CompileError, cell_index, compile_document, compile_workbook
from .compile_recording import compile_delta, compile_recording
from .house import css
from .localize import localize
from .qa import validate_script
from .render_deck import render_deck
from .render_recording import render_edit

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def run(out_dir: Path, with_video: bool = True) -> list[dict[str, Any]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    weekly_pack = _load("weekly.json")
    leadership = _load("leadership.json")
    launch = _load("launch.json")
    walkthrough = _load("walkthrough.json")
    sop = _load("sop.json")
    results: list[dict[str, Any]] = []

    weekly = _guard(
        results,
        "Weekly operating review",
        lambda: _deck(
            out_dir / "weekly" / "deck.html",
            compile_workbook(weekly_pack),
            cells=cell_index(weekly_pack),
        ),
    )
    _guard(
        results,
        "Leadership brief",
        lambda: _deck(out_dir / "leadership" / "deck.html", compile_document(leadership, "leadership-brief")),
    )
    _guard(
        results,
        "Launch announcement",
        lambda: _deck(out_dir / "launch" / "deck.html", compile_document(launch, "launch-announcement")),
    )
    walk = _guard(
        results,
        "Product walkthrough",
        lambda: _recording(out_dir / "walkthrough", walkthrough, "product-walkthrough", with_video),
    )
    _guard(
        results,
        "SOP training",
        lambda: _recording(out_dir / "sop", sop, "sop-training", with_video),
    )
    if walk and walk.get("script"):
        _guard(
            results,
            "Feature delta",
            lambda: _delta(out_dir / "delta", walk["script"], with_video),
        )
    if weekly and weekly.get("script"):
        _guard(results, "Localize, numbers locked", lambda: _localize_ok(out_dir / "localize", weekly["script"]))
        _expect_block(
            results,
            "Localize, number drift blocked",
            lambda: localize(weekly["script"], {2: "Net revenue is $5.10M, above target."}, "fr"),
        )
        quoted = answer(weekly["script"], "Where did net revenue land against target?")
        refused = answer(weekly["script"], "What is the competitor market share?")
        results.append(
            {
                "name": "Grounded chat quotes a beat",
                "status": "passed" if not quoted["refused"] and "4.82M" in quoted["text"] else "failed",
                "detail": quoted["text"],
                "href": None,
            }
        )
        results.append(
            {
                "name": "Grounded chat refuses",
                "status": "passed" if refused["refused"] else "failed",
                "detail": refused["text"],
                "href": None,
            }
        )
    empty = json.loads(json.dumps(weekly_pack))
    empty["kpis"][0]["value"] = None
    _expect_block(results, "Empty required KPI blocked", lambda: compile_workbook(empty))
    _write_index(out_dir, results)
    return results


def _deck(path: Path, script: dict[str, Any], cells: dict | None = None) -> dict[str, Any]:
    errors = validate_script(script, cells=cells)
    if errors:
        raise CompileError(errors)
    render_deck(script, path)
    path.with_name("script.json").write_text(json.dumps(script), encoding="utf-8")
    return {"script": script, "href": path}


def _recording(path: Path, fixture: dict[str, Any], skill_id: str, with_video: bool) -> dict[str, Any]:
    script = compile_recording(fixture["segments"], skill_id=skill_id, title=fixture["title"])
    errors = validate_script(script, duration_ms=script["source_duration_ms"])
    if errors:
        raise CompileError(errors)
    rendered = render_edit(script, path, with_video=with_video)
    if with_video and rendered.get("video_error"):
        raise CompileError([rendered["video_error"]])
    (path / "script.json").write_text(json.dumps(script), encoding="utf-8")
    return {"script": script, "href": rendered["storyboard"], "video": rendered.get("video")}


def _delta(path: Path, parent: dict[str, Any], with_video: bool) -> dict[str, Any]:
    script = compile_delta(
        parent,
        [
            {
                "t_start_ms": 0,
                "t_end_ms": 3600,
                "text": "A receipt toggle now sits under Billing.",
                "screen": "Billing",
            }
        ],
        changelog={"id": "c1", "text": "Receipts can now be turned on under Billing."},
    )
    kept = parent["beats"][0]["text"]
    if script["beats"][0]["text"] != kept:
        raise CompileError(["delta rewrote an unchanged beat"])
    errors = validate_script(script)
    if errors:
        raise CompileError(errors)
    rendered = render_edit(script, path, with_video=with_video)
    if with_video and rendered.get("video_error"):
        raise CompileError([rendered["video_error"]])
    return {"href": rendered["storyboard"], "video": rendered.get("video")}


def _localize_ok(path: Path, script: dict[str, Any]) -> dict[str, Any]:
    translated = localize(
        script,
        {
            2: "Le revenu net est de $4.82M, $220,000 au-dessus de l'objectif de $4.60M.",
        },
        "fr",
    )
    errors = validate_script(translated, cells=None)
    if errors:
        raise CompileError(errors)
    render_deck(translated, path / "deck.html")
    return {"href": path / "deck.html"}


def _guard(results: list[dict[str, Any]], name: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any] | None:
    try:
        payload = fn()
    except CompileError as exc:
        results.append({"name": name, "status": "failed", "detail": "; ".join(exc.errors), "href": None})
        return None
    href = payload.get("href")
    detail = ""
    video = payload.get("video")
    if video:
        detail = video.name
    results.append(
        {
            "name": name,
            "status": "passed",
            "detail": detail,
            "href": href,
        }
    )
    return payload


def _expect_block(results: list[dict[str, Any]], name: str, fn: Callable[[], Any]) -> None:
    try:
        fn()
    except CompileError as exc:
        results.append(
            {
                "name": name,
                "status": "blocked",
                "detail": "; ".join(exc.errors),
                "href": None,
            }
        )
        return
    results.append({"name": name, "status": "failed", "detail": "guard did not fire", "href": None})


def _write_index(out_dir: Path, results: list[dict[str, Any]]) -> None:
    items = []
    failed = False
    for result in results:
        if result["status"] == "failed":
            failed = True
        href = result.get("href")
        link = ""
        if href:
            rel = Path(href).resolve().relative_to(out_dir.resolve()).as_posix()
            link = f' — <a href="{rel}">open</a>'
        klass = {"passed": "pass", "blocked": "pass", "failed": "fail"}[result["status"]]
        detail = f" — {result['detail']}" if result.get("detail") else ""
        items.append(
            f'<li class="{klass}"><strong>{result["status"]}</strong> {result["name"]}{detail}{link}</li>'
        )
    banner = "One check failed." if failed else "Every check passed. Empty cells and drifted numbers stayed blocked."
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Grounded Studio</title>
<style>{css()}
.page {{ max-width: 960px; }}
video {{ width: 100%; background: #111; margin: 12px 0; }}
.ask {{ display: flex; gap: 8px; }}
.ask input {{ flex: 1; font: inherit; padding: 10px 12px; border: 1px solid var(--rule); background: white; }}
.ask button {{ font: inherit; padding: 10px 16px; background: var(--accent); color: var(--paper); border: 0; cursor: pointer; }}
</style></head>
<body><main class="page">
<h1>Grounded Studio</h1>
<p>{banner} The deck and the film share one house style. Chat quotes the weekly pack or refuses.</p>
<h2>Weekly operating review</h2>
<p><a href="weekly/deck.html">Open the deck</a>. Arrow keys move between slides. Each footer is a cell.</p>
<h2>Leadership brief</h2>
<p><a href="leadership/deck.html">Open the deck</a>. The sentence on each slide is the source sentence.</p>
<h2>Launch</h2>
<p><a href="launch/deck.html">Open the deck</a>.</p>
<h2>Billing walkthrough</h2>
<video controls src="walkthrough/walkthrough.mp4">
  <track kind="captions" srclang="en" src="walkthrough/captions.vtt" default>
</video>
<p><a href="walkthrough/source.mp4">Source recording</a> · <a href="walkthrough/storyboard.html">Storyboard</a> · <a href="walkthrough/guide.md">Guide</a></p>
<h2>Weekly close</h2>
<video controls src="sop/walkthrough.mp4"></video>
<p><a href="sop/guide.md">Numbered steps</a></p>
<h2>What changed</h2>
<video controls src="delta/walkthrough.mp4"></video>
<h2>Ask the weekly pack</h2>
<form class="ask" id="chat">
  <input name="question" placeholder="Where did net revenue land?" autocomplete="off">
  <button type="submit">Ask</button>
</form>
<p id="answer"></p>
<h2>Checks</h2>
<ul>
{''.join(items)}
</ul>
<script>
document.getElementById("chat").addEventListener("submit", async (event) => {{
  event.preventDefault();
  const question = new FormData(event.target).get("question");
  const answer = document.getElementById("answer");
  try {{
    const response = await fetch("/api/chat", {{
      method: "POST",
      headers: {{ "content-type": "application/json" }},
      body: JSON.stringify({{ question }})
    }});
    const body = await response.json();
    answer.textContent = body.refused ? body.text : body.text + "  " + (body.citation || "");
  }} catch (err) {{
    answer.textContent = "Open this page from the studio server to ask. python -m grounded.studio";
  }}
}});
</script>
</main></body></html>
"""
    (out_dir / "index.html").write_text(page, encoding="utf-8")


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("out/demo")
    results = run(out)
    for result in results:
        print(f"{result['status']:8} {result['name']}")
        if result.get("detail"):
            print(f"         {result['detail']}")
    if any(result["status"] == "failed" for result in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
