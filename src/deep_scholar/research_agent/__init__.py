"""Deep Scholar File Reconstruction Agent.

This module exposes prompts and tools for the file understanding workflow.
"""

from research_agent.prompts import (
    FILE_ANALYSIS_SUBAGENT_INSTRUCTIONS,
    FILE_RECONSTRUCTION_WORKFLOW_INSTRUCTIONS,
    FILE_REPORT_WRITING_GUIDELINES,
    STRUCTURE_PLANNING_SUBAGENT_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    TASK_DELEGATION_PREFIX,
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
    vectorize_text_tool,
)

__all__ = [
    "apply_file_mapping",
    "extract_pdf",
    "hash_file",
    "list_uploads",
    "ocr_image",
    "ocr_pdf",
    "read_text",
    "think_tool",
    "unpack_zip",
    "vectorize_text_tool",
    "FILE_ANALYSIS_SUBAGENT_INSTRUCTIONS",
    "FILE_RECONSTRUCTION_WORKFLOW_INSTRUCTIONS",
    "FILE_REPORT_WRITING_GUIDELINES",
    "STRUCTURE_PLANNING_SUBAGENT_INSTRUCTIONS",
    "SUBAGENT_DELEGATION_INSTRUCTIONS",
    "TASK_DELEGATION_PREFIX",
    "USER_INTENT_SUBAGENT_INSTRUCTIONS",
    "VALIDATION_SUBAGENT_INSTRUCTIONS",
]
