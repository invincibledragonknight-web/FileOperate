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

workspace_root = str(Path("./workspace").resolve())

composite_backend = lambda rt: CompositeBackend(
    default=LocalSandboxBackend(
        root_dir=".",
        virtual_mode=True,
        path_aliases={
            "/workspace": workspace_root,
        },
    ),
    routes={
        "/workspace/": LocalSandboxBackend(root_dir="./workspace", virtual_mode=True),
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




