from __future__ import annotations

from pathlib import Path

# Ensure the editable deepagents package is discoverable when running from repo root.
_LIB_ROOT = Path(__file__).resolve().parent / "libs" / "deepagents" / "deepagents"
if _LIB_ROOT.is_dir():
    __path__.append(str(_LIB_ROOT))  # type: ignore[name-defined]

from .graph import create_deep_agent
from .middleware.filesystem import FilesystemMiddleware
from .middleware.memory import MemoryMiddleware
from .middleware.subagents import CompiledSubAgent, SubAgent, SubAgentMiddleware
from .skills.middleware import SkillsMiddleware
from .skills.types import SkillMetadata

__all__ = [
    "CompiledSubAgent",
    "FilesystemMiddleware",
    "MemoryMiddleware",
    "SkillMetadata",
    "SkillsMiddleware",
    "SubAgent",
    "SubAgentMiddleware",
    "create_deep_agent",
]
