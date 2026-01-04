from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import ExecuteResponse, SandboxBackendProtocol
from langgraph.store.memory import InMemoryStore
import subprocess
from typing import Dict, Any
import pandas as pd
from langchain.tools import tool
from pathlib import Path
import os





class LocalSandboxBackend(FilesystemBackend, SandboxBackendProtocol):
    def __init__(
        self,
        *,
        root_dir: str | Path | None = None,
        virtual_mode: bool = True,
        timeout: float = 120.0,
        max_output_bytes: int = 200_000,
        env: dict[str, str] | None = None,
        path_aliases: dict[str, str] | None = None,
    ) -> None:
        super().__init__(root_dir=root_dir, virtual_mode=virtual_mode)
        self._timeout = timeout
        self._max_output_bytes = max_output_bytes
        self._env = env if env is not None else os.environ.copy()
        self._path_aliases = path_aliases or {}

    @property
    def id(self) -> str:
        return f"local:{self.cwd}"

    def _apply_path_aliases(self, command: str) -> str:
        if not self._path_aliases:
            return command
        updated = command
        for virtual_path, real_path in self._path_aliases.items():
            virtual_root = virtual_path.rstrip("/")
            real_root = str(Path(real_path).resolve()).rstrip("/")
            updated = updated.replace(f"{virtual_root}/", f"{real_root}/")
            updated = updated.replace(virtual_root, real_root)
        return updated

    def execute(self, command: str) -> ExecuteResponse:
        if not isinstance(command, str) or not command.strip():
            return ExecuteResponse(
                output="Error: execute expects a non-empty command string.",
                exit_code=1,
                truncated=False,
            )

        command = self._apply_path_aliases(command)
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.cwd),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                env=self._env,
            )
        except subprocess.TimeoutExpired:
            return ExecuteResponse(
                output=f"Error: Command timed out after {self._timeout:.1f} seconds.",
                exit_code=124,
                truncated=False,
            )

        output_parts: list[str] = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(result.stderr)
        output = "\n".join(output_parts) if output_parts else "<no output>"

        truncated = False
        if len(output) > self._max_output_bytes:
            output = output[: self._max_output_bytes]
            truncated = True

        return ExecuteResponse(output=output, exit_code=result.returncode, truncated=truncated)


# workspace_root = str(Path("./workspace").resolve())
# composite_backend = lambda rt: CompositeBackend(
#     default=LocalSandboxBackend(
#         root_dir=".",
#         virtual_mode=True,
#         path_aliases={
#             "/workspace": workspace_root,
#         },
#     ),
#     routes={
#         "/workspace/": LocalSandboxBackend(root_dir="./workspace", virtual_mode=True),
#     },
# )

# agent = create_deep_agent(
#     model=model,
#     tools=all_tools,
#     system_prompt=ORCHESTRATOR_SYSTEM_PROMPT + DELEGATION_INSTRUCTIONS,
#     subagents=[transcription_processing_agent],
#     backend=composite_backend,
# )
