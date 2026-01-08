from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    file_path: str
    allowed_tools: Optional[Sequence[str]] = None
