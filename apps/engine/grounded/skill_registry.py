"""Runtime loader for SKILL.md contracts.

The skill library is policy, not prose-only documentation. This module keeps
parsing intentionally dependency-free: contracts remain readable Markdown,
while a small stable header/list grammar is executable at runtime.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

_ID = re.compile(r"^#\s+(skill|craft):\s*([a-z0-9][a-z0-9-]*)\s*$", re.I)
_FIELD = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_-]*):\s*(.*?)\s*$")


class SkillRegistryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillContract:
    id: str
    kind: str
    version: str
    job: str
    path: Path
    crafts: tuple[str, ...] = ()
    contract_text: str = ""
    fields: tuple[tuple[str, str], ...] = ()
    lists: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def field(self, name: str, default: str = "") -> str:
        return dict(self.fields).get(name, default)

    def items(self, name: str) -> tuple[str, ...]:
        return dict(self.lists).get(name, ())

    @property
    def sha256(self) -> str:
        import hashlib

        return hashlib.sha256(self.contract_text.encode("utf-8")).hexdigest()

    def provenance(self) -> dict[str, object]:
        return {
            "skill_id": self.id,
            "skill_version": self.version,
            "skill_sha256": self.sha256,
            "skill_path": _display_path(self.path),
            "crafts": list(self.crafts),
            "contract_text": self.contract_text,
        }


def skills_root(explicit: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("GROUNDED_SKILLS_ROOT"):
        candidates.append(Path(os.environ["GROUNDED_SKILLS_ROOT"]))
    here = Path(__file__).resolve()
    candidates.extend(
        [
            Path.cwd() / "skills",
            here.parents[3] / "skills",
            Path("/app/skills"),
        ]
    )
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    raise SkillRegistryError("skills directory is not available at runtime")


def load_contract(skill_id: str, root: str | Path | None = None) -> SkillContract:
    base = skills_root(root)
    direct = base / skill_id / "SKILL.md"
    craft = base / "_crafts" / skill_id / "SKILL.md"
    path = direct if direct.is_file() else craft
    if not path.is_file():
        raise SkillRegistryError(f"unknown skill or craft {skill_id!r}")
    return parse_contract(path)


def resolve_skill(skill_id: str, root: str | Path | None = None) -> tuple[SkillContract, tuple[SkillContract, ...]]:
    contract = load_contract(skill_id, root)
    if contract.kind != "skill":
        raise SkillRegistryError(f"{skill_id!r} is a craft, not a top-level skill")
    crafts: list[SkillContract] = []
    for craft_id in contract.crafts:
        craft = load_contract(craft_id, root)
        if craft.kind != "craft":
            raise SkillRegistryError(f"{craft_id!r} is not a craft")
        crafts.append(craft)
    return contract, tuple(crafts)


def parse_contract(path: str | Path) -> SkillContract:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines:
        raise SkillRegistryError(f"empty skill contract: {source}")
    match = _ID.match(lines[0].strip())
    if not match:
        raise SkillRegistryError(f"bad skill header in {source}")
    kind, contract_id = match.group(1).lower(), match.group(2).lower()

    fields: dict[str, str] = {}
    crafts: list[str] = []
    lists: dict[str, list[str]] = {}
    list_name: str | None = None
    for raw in lines[1:]:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            if stripped.startswith("#"):
                list_name = None
            continue
        field = _FIELD.match(stripped)
        if field and not stripped.startswith("-"):
            key, value = field.group(1).lower(), field.group(2).strip()
            fields[key] = value
            list_name = key if value == "" else None
            continue
        if stripped.startswith("-") and list_name:
            item = stripped[1:].strip()
            lists.setdefault(list_name, []).append(item)
            if list_name == "crafts_required":
                craft_id = re.split(r"\s+when\s+", item, maxsplit=1, flags=re.I)[0].strip()
                if craft_id:
                    crafts.append(craft_id)

    version = fields.get("version")
    if not version:
        raise SkillRegistryError(f"{source} has no version")
    return SkillContract(
        id=contract_id,
        kind=kind,
        version=version,
        job=fields.get("job", ""),
        path=source,
        crafts=tuple(dict.fromkeys(crafts)),
        contract_text=text,
        fields=tuple(sorted(fields.items())),
        lists=tuple((key, tuple(values)) for key, values in sorted(lists.items())),
    )


def _display_path(path: Path) -> str:
    parts = path.as_posix().split("/")
    if "skills" in parts:
        return "/".join(parts[parts.index("skills"):])
    return path.name


def catalog(root: str | Path | None = None) -> tuple[SkillContract, ...]:
    base = skills_root(root)
    found: list[SkillContract] = []
    for path in sorted(base.glob("*/SKILL.md")):
        found.append(parse_contract(path))
    return tuple(found)


def execution_provenance(skill_id: str, root: str | Path | None = None) -> dict[str, object]:
    skill, crafts = resolve_skill(skill_id, root)
    from .contracts import runtime_for

    runtime = runtime_for(skill, crafts)
    return {
        **skill.provenance(),
        "craft_versions": {craft.id: craft.version for craft in crafts},
        "craft_sha256": {craft.id: craft.sha256 for craft in crafts},
        "craft_contracts": {craft.id: craft.contract_text for craft in crafts},
        "runtime": runtime.describe(),
    }
