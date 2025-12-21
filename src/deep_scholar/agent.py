"""File Reconstruction Agent - Standalone script for LangGraph deployment.

This module creates a file understanding and reconstruction agent with custom tools
and deterministic prompts for file inventory, semantic extraction, planning, and execution.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from research_agent.prompts import (
    FILE_ANALYSIS_SUBAGENT_INSTRUCTIONS,
    FILE_RECONSTRUCTION_WORKFLOW_INSTRUCTIONS,
    FILE_REPORT_WRITING_GUIDELINES,
    STRUCTURE_PLANNING_SUBAGENT_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    USER_INTENT_SUBAGENT_INSTRUCTIONS,
    VALIDATION_SUBAGENT_INSTRUCTIONS,
)
from research_agent.tools import (
    apply_file_mapping,
    extract_pdf,
    hash_file,
    list_uploads,
    ocr_image,
    ocr_pdf,
    read_text,
    think_tool,
    unpack_zip,
)

# Load environment variables early so they are available to the backend/model
load_dotenv()

# Limits
max_concurrent_file_units = 3
max_file_iterations = 3

# Combine orchestrator instructions
INSTRUCTIONS = (
    FILE_RECONSTRUCTION_WORKFLOW_INSTRUCTIONS
    + "\n\n"
    + FILE_REPORT_WRITING_GUIDELINES
    + "\n\n"
    + "=" * 80
    + "\n\n"
    + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
        max_concurrent_file_units=max_concurrent_file_units,
        max_file_iterations=max_file_iterations,
    )
)

# Sub-agents
file_analysis_sub_agent = {
    "name": "file-analysis",
    "description": "OCR, parsing, metadata extraction, and document classification.",
    "system_prompt": FILE_ANALYSIS_SUBAGENT_INSTRUCTIONS,
    "tools": [
        list_uploads,
        read_text,
        extract_pdf,
        ocr_pdf,
        ocr_image,
        hash_file,
        think_tool,
    ],
}

intent_modeler_sub_agent = {
    "name": "intent-modeler",
    "description": "Interpret user intent and constraints from /user_intent.md.",
    "system_prompt": USER_INTENT_SUBAGENT_INSTRUCTIONS,
    "tools": [think_tool],
}

structure_planner_sub_agent = {
    "name": "structure-planner",
    "description": "Propose a hierarchy and naming scheme based on semantics and intent.",
    "system_prompt": STRUCTURE_PLANNING_SUBAGENT_INSTRUCTIONS,
    "tools": [think_tool],
}

validator_sub_agent = {
    "name": "validator",
    "description": "Validate proposed structure for completeness and conflicts.",
    "system_prompt": VALIDATION_SUBAGENT_INSTRUCTIONS,
    "tools": [think_tool],
}


def resolve_paths() -> dict:
    """Resolve the single filesystem root used by the agent backend."""
    base_dir = Path(__file__).resolve().parents[2]
    work_root = os.getenv(
        "DEEP_SCHOLAR_WORK_ROOT",
        str(base_dir / "data" / "work"),
    )

    return {"work_root": work_root}


def ensure_dir(path_str: str) -> str:
    Path(path_str).mkdir(parents=True, exist_ok=True)
    return path_str


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


paths = resolve_paths()
work_root = ensure_dir(paths["work_root"])

# Keep all agent artifacts and file operations under the work root.
backend = FilesystemBackend(root_dir=work_root, virtual_mode=True)

model = build_model()

# Create the agent
agent = create_deep_agent(
    model=model,
    tools=[
        think_tool,
        list_uploads,
        unpack_zip,
        read_text,
        extract_pdf,
        ocr_pdf,
        ocr_image,
        hash_file,
        apply_file_mapping,
    ],
    system_prompt=INSTRUCTIONS,
    subagents=[
        file_analysis_sub_agent,
        intent_modeler_sub_agent,
        structure_planner_sub_agent,
        validator_sub_agent,
    ],
    backend=backend,
)
