# %%
from dotenv import load_dotenv

load_dotenv(".env", override=True)

# %% [markdown]
# # Local Storage Deepagent (Tree View)
# 
# This notebook-style script mirrors the research quickstart format, but for the file-oriented deep agent. It keeps planning/synthesis in root-level internal artifacts and delegates external inspection to a tree-view sub-agent.

# %% [markdown]
# ## Task-Specific Tools
# 
# We only expose the `tree_view` inspection tool to the external sub-agent. The orchestrator should delegate to it rather than calling filesystem tools directly.
from pathlib import Path
from langchain.tools import tool

from pathlib import Path

WORKSPACE_ROOT = Path("./workspace").resolve()

def resolve_workspace_path(virtual_path: str) -> Path:
    """
    Resolve a virtual workspace path into a real filesystem path.

    Accepts:
    - /workspace
    - /workspace/
    - /workspace/relative/path

    Rejects:
    - Any path outside the workspace namespace
    - Any path attempting directory traversal
    """

    if virtual_path == "/workspace":
        return WORKSPACE_ROOT

    if virtual_path.startswith("/workspace/"):
        relative = virtual_path[len("/workspace/") :]
        real_path = (WORKSPACE_ROOT / relative).resolve()
    else:
        raise ValueError(f"Invalid workspace path: {virtual_path}")

    # Enforce sandboxing
    if not str(real_path).startswith(str(WORKSPACE_ROOT)):
        raise ValueError(f"Path traversal detected: {virtual_path}")

    return real_path


import zipfile
@tool(parse_docstring=True)
def unzip_workspace_file(virtual_zip_path: str) -> dict:
    """
Unzip a ZIP archive located inside the workspace.

This preprocessing function extracts the contents of a ZIP file referenced
by a virtual workspace path. The archive is unpacked into a directory with
the same base name as the ZIP file, located in the same workspace directory.

The function operates strictly within the workspace sandbox:
- Input paths are virtual (e.g. `/workspace/foo.zip`)
- Execution is performed on resolved real paths
- Output paths are returned in virtual-path form for agent consumption

Typical agent usage:
- Call this when a ZIP file is detected during workspace inspection
- Follow with a tree-view operation on the extracted directory

Args:
    virtual_zip_path: Virtual path to a ZIP file inside the workspace
        (for example `/workspace/datasets/images.zip`).

Returns:
    A dictionary containing:
    - status: Execution status string
    - zip: The input virtual ZIP path
    - extracted_to: Virtual path of the extracted directory
    - num_files: Number of files listed in the ZIP archive

Raises:
    FileNotFoundError: If the ZIP file does not exist.
    ValueError: If the provided path does not point to a ZIP archive.
"""

    zip_path = resolve_workspace_path(virtual_zip_path)

    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    if zip_path.suffix.lower() != ".zip":
        raise ValueError("Provided file is not a zip archive")

    output_dir = zip_path.with_suffix("")
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(output_dir)

    return {
        "status": "ok",
        "zip": virtual_zip_path,
        "extracted_to": f"/workspace/{output_dir.name}",
        "num_files": len(zf.namelist()),
    }
#%%
@tool(parse_docstring=True)
def tree_view_workspace(
    virtual_path: str,
    max_depth: int = 4,
    max_entries: int = 200,
) -> dict:
    """
Generate a hierarchical tree view of a workspace directory.

This preprocessing function inspects the directory structure rooted at a
given virtual workspace path and produces a readable tree representation.
It is designed for lightweight structural understanding rather than full
content analysis.

The function supports depth and entry limits to prevent excessive output
and is suitable for agent-driven exploration and reporting.

Typical agent usage:
- Inspect workspace contents before deciding on further preprocessing
- Summarize directory layout in reports such as `/final_report.md`
- Validate results of prior operations such as unzip or file generation

Args:
    virtual_path: Virtual workspace path to inspect, such as `/workspace`
        or `/workspace/data`.
    max_depth: Maximum directory depth to traverse. The default value limits
        traversal to a small number of levels to avoid excessive output.
    max_entries: Maximum total number of files or directories to include
        in the output. The default value prevents large directories from
        producing oversized results.

Returns:
    A dictionary containing:
    - root: The inspected virtual path
    - max_depth: The depth limit used during traversal
    - entries: Number of directory entries included
    - tree: A newline-separated string representing the directory tree
    - truncated: Whether traversal stopped early due to entry limits

Raises:
    FileNotFoundError: If the target path does not exist.
"""

    root = resolve_workspace_path(virtual_path)

    if not root.exists():
        raise FileNotFoundError(root)

    lines = []
    count = 0

    def walk(path: Path, prefix: str = "", depth: int = 0):
        nonlocal count
        if depth > max_depth or count >= max_entries:
            return

        for p in sorted(path.iterdir()):
            if count >= max_entries:
                return

            lines.append(f"{prefix}{p.name}")
            count += 1

            if p.is_dir():
                walk(p, prefix + "  ", depth + 1)

    walk(root)

    return {
        "root": virtual_path,
        "max_depth": max_depth,
        "entries": count,
        "tree": "\n".join(lines),
        "truncated": count >= max_entries,
    }

#%%
all_tools = [
    tree_view_workspace,
    unzip_workspace_file
]

# %% [markdown]
# ## Prompt Helpers
# 
# Minimal helpers to display prompts and messages (inspired by the research quickstart utils).

# %%
import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def show_prompt(prompt_text: str, title: str = "Prompt", border_style: str = "blue"):
    """Display a prompt with simple highlighting."""
    formatted_text = Text(prompt_text)
    formatted_text.highlight_regex(r"<[^>]+>", style="bold blue")
    formatted_text.highlight_regex(r"##[^#\n]+", style="bold magenta")
    formatted_text.highlight_regex(r"###[^#\n]+", style="bold cyan")
    console.print(
        Panel(
            formatted_text,
            title=f"[bold green]{title}[/bold green]",
            border_style=border_style,
            padding=(1, 2),
        )
    )


def format_message_content(message):
    """Render message content, including tool calls when present."""
    parts = []
    tool_calls_processed = False

    if isinstance(message.content, str):
        parts.append(message.content)
    elif isinstance(message.content, list):
        for item in message.content:
            if item.get("type") == "text":
                parts.append(item["text"])
            elif item.get("type") == "tool_use":
                parts.append(f"\n🔧 Tool Call: {item['name']}")
                parts.append(f"   Args: {json.dumps(item['input'], indent=2)}")
                parts.append(f"   ID: {item.get('id', 'N/A')}")
                tool_calls_processed = True
    else:
        parts.append(str(message.content))

    if not tool_calls_processed and hasattr(message, "tool_calls") and message.tool_calls:
        for tool_call in message.tool_calls:
            parts.append(f"\n🔧 Tool Call: {tool_call['name']}")
            parts.append(f"   Args: {json.dumps(tool_call['args'], indent=2)}")
            parts.append(f"   ID: {tool_call['id']}")

    return "\n".join(parts)


def format_messages(messages):
    """Pretty-print a list of messages."""
    for m in messages:
        msg_type = m.__class__.__name__.replace("Message", "")
        content = format_message_content(m)

        if msg_type == "Human":
            console.print(Panel(content, title="🧑 Human", border_style="blue"))
        elif msg_type == "Ai":
            console.print(Panel(content, title="🤖 Assistant", border_style="green"))
        elif msg_type == "Tool":
            console.print(Panel(content, title="🔧 Tool Output", border_style="yellow"))
        else:
            console.print(Panel(content, title=f"📝 {msg_type}", border_style="white"))


def format_message(m):
    """Pretty-print a list of messages."""
    msg_type = m.__class__.__name__.replace("Message", "")
    content = format_message_content(m)

    if msg_type == "Human":
        console.print(Panel(content, title="🧑 Human", border_style="blue"))
    elif msg_type == "Ai":
        console.print(Panel(content, title="🤖 Assistant", border_style="green"))
    elif msg_type == "Tool":
        console.print(Panel(content, title="🔧 Tool Output", border_style="yellow"))
    else:
        console.print(Panel(content, title=f"📝 {msg_type}", border_style="white"))

# %% [markdown]
# ## Task-Specific Instructions
# 
# Orchestrator prompt enforces internal vs external separation; sub-agent prompt restricts to tree inspection only.

# %%
# from file_agent_compact import (
#     FILE_PROCESSOR_SYSTEM_PROMPT,
#     ORCHESTRATOR_SYSTEM_PROMPT,
# )
ORCHESTRATOR_SYSTEM_PROMPT = """
Your job is to fullfill user's request step-by-step

# Rule of using different storage

1. the /final_report.md /plan.md /todo-list.md /file-summary.md /plan-hierarchical.md etc. all the files as a general perspective understanding or plan must be stored in the / root level
2. all the input files, are stored in the /workspace and therefore user's reference to user-provided files are located here

"""
show_prompt(ORCHESTRATOR_SYSTEM_PROMPT, title="Orchestrator Prompt")
# show_prompt(
#     FILE_PROCESSOR_SYSTEM_PROMPT,
#     title="External File Processor Prompt",
#     border_style="green",
# )



# %% [markdown]
# ## Create the Agent
# 
# Build the orchestrator with built-in tools and the external sub-agent. Swap the model as needed.

# %%
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI

# Default model; replace with any LangChain-compatible chat model
# model = init_chat_model(model="anthropic:claude-sonnet-4-5-20250929", temperature=0.0)

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


model = build_model()

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore
from deepagents.backends import FilesystemBackend


composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/workspace/": FilesystemBackend(root_dir="./workspace", virtual_mode=True),
    }
)

agent = create_deep_agent(
    model=model,
    tools=all_tools,
    system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
    subagents=[],
    backend=composite_backend
)

# %%
# Visualize the graph (optional)
try:
    from IPython.display import Image, display

    display(Image(agent.get_graph().draw_mermaid_png()))
except Exception:
    console.print("Graph visualization unavailable in this environment.", style="red")

# %% [markdown]
# ## Example Invocation
# 
# Ask the agent to render a shallow tree for the current directory. Adjust depth or entries as needed.

# %%
request_message = {
        "messages": [
            {
                "role": "user",
                "content": "Discover all the files in your workspace directory unzip the existing files, and generate a tree view and summarize the files and return me with a /final_report.md",
            }
        ],
    }

#%%
example_result = agent.invoke(
    request_message
)

format_messages(example_result["messages"])

# %% [markdown]
# You can read internal artifacts (e.g., `/research.md`, `/report.md`) from `example_result["files"]` if the run produced them.
for event in agent.stream(
    request_message
):
    print(event)
# %%
