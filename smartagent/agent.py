from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend
from langchain_openai import ChatOpenAI

from smartagent.tools import ALL_TOOLS, think_tool
from smartagent.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    ORCHESTRATOR_SANDBOX_SYSTEM_PROMPT,
    DELEGATION_INSTRUCTIONS,
    TRANSCRIPT_POSTPROCESSOR_INSTRUCTIONS,
    current_date,
)

transcription_processing_agent = {
    "name": "transcription-processing-agent",
    "description": "Refine noisy audio transcription and generate structured meeting minutes. No external research.",
    "system_prompt": TRANSCRIPT_POSTPROCESSOR_INSTRUCTIONS.format(date=current_date),
    "tools": [think_tool],
}


def build_model():
    """Pick the default LLM based on environment-driven provider selection."""
    provider = (os.getenv("DEEP_SCHOLAR_LLM_PROVIDER") or "iflow").lower()

    if provider == "deepseek":
        return ChatOpenAI(
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
        )

    if provider == "llama":
        return ChatOpenAI(
            base_url=os.getenv("LLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("LLAMA_API_KEY"),
            model=os.getenv("LLAMA_MODEL", "llama3"),
            temperature=float(os.getenv("LLAMA_TEMPERATURE", "0.2")),
        )

    # Default: IFlow (qwen3-max)
    return ChatOpenAI(
        base_url=os.getenv("IFLOW_BASE_URL", "https://apis.iflow.cn/v1"),
        api_key=os.getenv("IFLOW_API_KEY"),
        model=os.getenv("IFLOW_MODEL", "qwen3-max"),
        temperature=float(os.getenv("IFLOW_TEMPERATURE", "0.2")),
    )



def build_agent(
    composite_backend,
    skills_dirs: Sequence[str | Path | tuple[str | Path, str]] | str | Path | None = None,
):
    model = build_model()

    return create_deep_agent(
        model=model,
        tools=ALL_TOOLS,
        # system_prompt=ORCHESTRATOR_SYSTEM_PROMPT + DELEGATION_INSTRUCTIONS,
        system_prompt = ORCHESTRATOR_SANDBOX_SYSTEM_PROMPT + DELEGATION_INSTRUCTIONS,
        subagents=[transcription_processing_agent],
        backend=composite_backend,
        skills_dirs=skills_dirs,
        interrupt_on={
            "move_workspace_file": {
                "allowed_decisions": ["approve", "edit", "reject"]
            },
        }
    )
