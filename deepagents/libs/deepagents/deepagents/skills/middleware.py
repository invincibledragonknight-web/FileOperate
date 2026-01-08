from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from langchain.agents.middleware.types import AgentMiddleware, AgentState, ModelRequest, ModelResponse
from typing_extensions import NotRequired

from deepagents.skills.load import list_skills, normalize_skills_dirs

SKILLS_STATE_KEY = "skills_metadata"


class SkillsState(AgentState):
    skills_metadata: NotRequired[list[dict[str, Any]]]


def render_skills_system_prompt(skills: Sequence[dict[str, Any]]) -> str:
    if not skills:
        return ""
    lines = [
        "You have access to a set of optional Skills.",
        "Skills are folders containing a SKILL.md file.",
        "Only the metadata is loaded by default. If a skill seems relevant, read its SKILL.md using filesystem tools.",
        "",
        "Available skills:",
    ]
    for skill in skills:
        name = str(skill.get("name") or "").strip()
        description = str(skill.get("description") or "").strip()
        path = str(skill.get("file_path") or "").strip()
        if name:
            if description:
                lines.append(f"- {name}: {description} (read {path})")
            else:
                lines.append(f"- {name}: (read {path})")
    return "\n".join(lines).strip()


class SkillsMiddleware(AgentMiddleware):
    state_schema = SkillsState

    def __init__(
        self,
        *,
        skills_dirs: Sequence[str | Path | tuple[str | Path, str]] | str | Path,
        state_key: str = SKILLS_STATE_KEY,
    ) -> None:
        self.skills_dirs = normalize_skills_dirs(skills_dirs)
        self.state_key = state_key
        self.tools = []

    def before_agent(self, state: dict[str, Any], runtime: Any) -> dict[str, Any]:
        skills = list_skills(self.skills_dirs)
        return {self.state_key: [asdict(skill) for skill in skills]}

    async def abefore_agent(self, state: dict[str, Any], runtime: Any) -> dict[str, Any]:
        return self.before_agent(state, runtime)

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        skills = request.state.get(self.state_key, [])
        block = render_skills_system_prompt(skills)
        if block:
            system_prompt = request.system_prompt
            updated = f"{system_prompt}\n\n{block}" if system_prompt else block
            request = request.override(system_prompt=updated)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        skills = request.state.get(self.state_key, [])
        block = render_skills_system_prompt(skills)
        if block:
            system_prompt = request.system_prompt
            updated = f"{system_prompt}\n\n{block}" if system_prompt else block
            request = request.override(system_prompt=updated)
        return await handler(request)
