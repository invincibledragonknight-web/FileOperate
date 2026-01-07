from __future__ import annotations

from dotenv import load_dotenv

from smartagent.renderer import _DEFAULT_RENDERER
from smartagent.agent import build_agent
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore
from deepagents.backends import FilesystemBackend


#--- SANDBOX ---
from smartagent.sandbox import LocalSandboxBackend
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
workspace_root = str((_REPO_ROOT / "workspace").resolve())
skills_root = str((_REPO_ROOT / "skills").resolve())
# Load .env file
load_dotenv(
    Path.joinpath(_REPO_ROOT, ".env"),
    override=True,
)
composite_backend = lambda rt: CompositeBackend(
    default=LocalSandboxBackend(
        root_dir=".",
        virtual_mode=True,
        path_aliases={
            "/workspace": workspace_root,
        },
    ),
    routes={
        "/workspace/": LocalSandboxBackend(
            root_dir=str(_REPO_ROOT / "workspace"),
            virtual_mode=True,
        ),
    },
)

# composite_backend = lambda rt: CompositeBackend(
#     default=StateBackend(rt),
#     routes={
#         "/workspace/": FilesystemBackend(root_dir="./workspace", virtual_mode=True),
#     },
# )

load_dotenv(".env", override=True)

agent = build_agent(composite_backend)




if __name__ == "__main__":
    final_state = None
    request_message = {
        "role": "user",
        "content": "Create a text file named hello.txt with the content 'Hello, World!' and a markdown file named info.md with a brief description about SmartAgent.",
    }
    for mode, chunk in agent.stream(
        request_message,
        stream_mode=["updates", "values"],  # stream deltas + full state
    ):
        if mode == "updates":
            # Your existing Rich renderer expects a dict event
            _DEFAULT_RENDERER.render_stream_event(chunk)
        elif mode == "values":
            # Keep overwriting; the last one is the final state
            final_state = chunk

    # Now you have the final output (messages + files) without invoking again
    _DEFAULT_RENDERER.render_final_output(final_state)
    print(final_state.get("files", {}))
