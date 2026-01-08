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

_REPO_ROOT = Path(__file__).resolve().parents[1]
workspace_root = str((_REPO_ROOT / "workspace").resolve())
skills_root = str((_REPO_ROOT / "skills").resolve())
# Load .env file
load_dotenv(
    Path.joinpath(_REPO_ROOT, ".env"),
    override=True,
)
composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/workspace/": LocalSandboxBackend(
            root_dir=str(_REPO_ROOT / "workspace"),
            virtual_mode=True,
        ),
        "/skills/": LocalSandboxBackend(
            root_dir=str(_REPO_ROOT / "skills"),
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

agent = build_agent(
    composite_backend,
    skills_dirs=[(skills_root, "/skills")],
)




if __name__ == "__main__":
    final_state = None
    request_dict = {
        "report generation": "Write me a /final_report.md based on the files from the zip file inside the /workspace, write the summary report in pure Chinese, make it extremly long and detailed, use as many as references from Chinese Commnunist Party history or Communism Theory as possible, make it official and academic style, targeting as a report for the central standing committee of the Communist Party of China.",

        "excel_analysis1": "我希望了解给出的excel的整体情况，其中我想知道来自山西省的有哪些人？硕士学历以及更高学历的有哪些人？",
        "meeting_minutes": "我有一个会议的录音文件，我希望生成一份完整详细正规的会议纪要。",
        "tmp_request": "What skills do you have?."
    }
    request_message = {
        "messages": [
            {
                "role": "user",
                "content": request_dict["tmp_request"],
            }
        ],
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
    # print(final_state.get("files", {}))
