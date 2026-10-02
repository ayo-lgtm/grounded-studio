"""Read the on-disk skill library. Skills are playbooks, not remote packages."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class CatalogError(Exception):
    pass


def content_root() -> Path:
    env = (os.environ.get("GROUNDED_ROOT") or "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "skills").is_dir() and (parent / "docs").is_dir():
            return parent
    return here.parents[1]


def load_catalog(root: Path | None = None) -> list[dict[str, Any]]:
    """Installable skills (not crafts). Every file must say offline: true."""
    base = root or (content_root() / "skills")
    if not base.is_dir():
        raise CatalogError(f"skills directory missing: {base}")
    items: list[dict[str, Any]] = []
    for path in sorted(base.glob("*/SKILL.md")):
        if path.parent.name.startswith("_"):
            continue
        meta = _parse(path, base)
        if meta.get("offline") is not True:
            raise CatalogError(f"{path} must set offline: true")
        if str(meta["id"]).startswith("scenario-"):
            raise CatalogError(f"refusing cloud skill id {meta['id']}")
        items.append(meta)
    return items


def load_crafts(root: Path | None = None) -> list[dict[str, Any]]:
    base = (root or (content_root() / "skills")) / "_crafts"
    if not base.is_dir():
        return []
    crafts: list[dict[str, Any]] = []
    for path in sorted(base.glob("*/SKILL.md")):
        meta = _parse(path, base)
        if meta.get("offline") is not True:
            raise CatalogError(f"{path} must set offline: true")
        meta["craft"] = True
        crafts.append(meta)
    return crafts


def _relative(path: Path, base: Path) -> str:
    anchor = base.parent if base.name in {"skills", "_crafts"} else base
    try:
        return str(path.relative_to(anchor))
    except ValueError:
        return path.name


def _parse(path: Path, base: Path) -> dict[str, Any]:
    kind = "skill"
    ident = path.parent.name
    version = ""
    offline = False
    area = ""
    job = ""
    for line in path.read_text(encoding="utf-8").splitlines()[:40]:
        stripped = line.strip()
        if stripped.startswith("# skill:"):
            kind = "skill"
            ident = stripped.split(":", 1)[1].strip() or ident
        elif stripped.startswith("# craft:"):
            kind = "craft"
            ident = stripped.split(":", 1)[1].strip() or ident
        elif stripped.startswith("version:"):
            version = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("offline:"):
            offline = stripped.split(":", 1)[1].strip().lower() == "true"
        elif stripped.startswith("area:"):
            area = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("job:"):
            job = stripped.split(":", 1)[1].strip()
    return {
        "id": ident,
        "kind": kind,
        "version": version or "1.0.0",
        "offline": offline,
        "area": area,
        "job": job,
        "path": _relative(path, base),
    }
