from __future__ import annotations

from pathlib import Path
from typing import List, Sequence
import re

import yaml

from deepagents.skills.types import SkillMetadata

_FRONTMATTER_RE = re.compile(r"\A---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|$)", re.DOTALL)


def _parse_frontmatter(text: str) -> dict:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}
    return data or {}


def _normalize_virtual_root(virtual_root: str) -> str:
    normalized = virtual_root.replace("\\", "/").strip()
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    return normalized.rstrip("/")


def _default_virtual_path(skill_md: Path) -> str:
    try:
        relative = skill_md.resolve().relative_to(Path.cwd())
    except ValueError:
        return skill_md.as_posix()
    return f"/{relative.as_posix()}"


def _resolve_skill_path(skill_md: Path, root: Path, virtual_root: str | None) -> str:
    if virtual_root:
        relative = skill_md.relative_to(root)
        return f"{virtual_root}/{relative.as_posix()}"
    return _default_virtual_path(skill_md)


def normalize_skills_dirs(
    skills_dirs: Sequence[str | Path | tuple[str | Path, str]] | str | Path | tuple[str | Path, str],
) -> list[str | Path | tuple[str | Path, str]]:
    if isinstance(skills_dirs, (str, Path)):
        return [skills_dirs]
    if (
        isinstance(skills_dirs, tuple)
        and len(skills_dirs) == 2
        and isinstance(skills_dirs[0], (str, Path))
        and isinstance(skills_dirs[1], str)
        and skills_dirs[1].startswith("/")
    ):
        return [skills_dirs]
    return list(skills_dirs)


def list_skills(
    skills_dirs: Sequence[str | Path | tuple[str | Path, str]] | str | Path,
) -> List[SkillMetadata]:
    out: List[SkillMetadata] = []
    roots = normalize_skills_dirs(skills_dirs)
    for root in roots:
        virtual_root = None
        root_entry = root
        if isinstance(root, tuple):
            if len(root) != 2:
                raise ValueError("skills_dirs tuples must be (path, virtual_root)")
            root_entry, virtual_root = root
        root_path = Path(root_entry).expanduser()
        if not root_path.exists() or not root_path.is_dir():
            continue
        normalized_virtual_root = _normalize_virtual_root(virtual_root) if virtual_root else None
        for skill_md in root_path.rglob("SKILL.md"):
            try:
                raw = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            meta = _parse_frontmatter(raw)
            name = str(meta.get("name") or skill_md.parent.name).strip()
            description = str(meta.get("description") or "").strip()
            allowed_tools = meta.get("allowed-tools") or meta.get("allowed_tools")
            if isinstance(allowed_tools, (list, tuple)):
                allowed_tools = [str(tool) for tool in allowed_tools]
            else:
                allowed_tools = None
            out.append(
                SkillMetadata(
                    name=name,
                    description=description,
                    file_path=_resolve_skill_path(skill_md, root_path, normalized_virtual_root),
                    allowed_tools=allowed_tools,
                )
            )
    out.sort(key=lambda skill: skill.name.lower())
    return out
