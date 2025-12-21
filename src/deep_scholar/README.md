# Deep Scholar File Reconstruction

## Quickstart

**Prerequisites**: Install [uv](https://docs.astral.sh/uv/) package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Ensure you are in the `deep_scholar` directory:
```bash
cd src/deep_scholar
```

Install packages:
```bash
uv sync
```

Set your API keys and storage root in `.env` (or export them):

```bash
# Agent work root (all artifacts, inputs, outputs, and FAISS index live here)
DEEP_SCHOLAR_WORK_ROOT=/absolute/path/to/data/work
#
# The agent will create and use these subfolders under the work root:
# - uploads/ (incoming files)
# - raw/ (immutable archive copies)
# - output/ (reconstructed files)
# - db/ (FAISS indices)

# Embeddings endpoint for FAISS ingestion (optional)
DEEP_SCHOLAR_EMBEDDING_BASE_URL=http://127.0.0.1:8081/v1
DEEP_SCHOLAR_EMBEDDING_API_KEY=local-llama
DEEP_SCHOLAR_EMBEDDING_MODEL=qwen3-embed

# Optional local VLM (for OCR)
DEEP_SCHOLAR_VLM_BASE_URL=http://127.0.0.1:8081/v1
DEEP_SCHOLAR_VLM_API_KEY=local-llama
DEEP_SCHOLAR_VLM_MODEL=qwen3-vl

# Primary LLM selector: iflow | deepseek | llama
DEEP_SCHOLAR_LLM_PROVIDER=iflow

# IFlow (OpenAI-compatible) defaults
IFLOW_BASE_URL=https://apis.iflow.cn/v1
IFLOW_API_KEY=your_iflow_api_key_here
IFLOW_MODEL=qwen3-max
IFLOW_TEMPERATURE=0.2

# DeepSeek (OpenAI-compatible)
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TEMPERATURE=0.2

# Local Llama (OpenAI-compatible endpoint such as Ollama/LM Studio)
LLAMA_BASE_URL=http://localhost:11434/v1
LLAMA_API_KEY=
LLAMA_MODEL=llama3
LLAMA_TEMPERATURE=0.2

# Anthropic API Key (optional, if you switch provider)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# OpenAI API Key (optional, if you switch provider)
OPENAI_API_KEY=your_openai_api_key_here

# LangSmith API Key (required for LangGraph local server)
# Get your key at: https://smith.langchain.com/settings
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here
```

## Usage Options

You can run this quickstart in two ways:

### Option 1: Jupyter Notebook

Run the interactive notebook to step through the file reconstruction agent:

```bash
uv run jupyter notebook research_agent.ipynb
```

### Option 2: LangGraph Server

Run a local [LangGraph server](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/) with a web interface:

```bash
langgraph dev
```

You can also connect the LangGraph server to a UI designed for deepagents:

```bash
$ git clone https://github.com/langchain-ai/deep-agents-ui.git
$ cd deep-agents-ui
$ yarn install
$ yarn dev
```

Then follow the instructions in the [deep-agents-ui README](https://github.com/langchain-ai/deep-agents-ui?tab=readme-ov-file#connecting-to-a-langgraph-server) to connect the UI to the running LangGraph server.

If you use the UI, configure its upload directory to point at
`<DEEP_SCHOLAR_WORK_ROOT>/uploads` so all files remain under the single work root.

## System Overview

Deep Scholar is a deterministic, artifact-driven workflow for file understanding and reconstruction. The agent:

1. Captures user intent in `/user_intent.md`.
2. Inventories inputs into `/file_inventory.json`.
3. Delegates OCR and semantic extraction to sub-agents.
4. Normalizes document semantics in `/doc_semantics.json`.
5. Proposes a hierarchy in `/proposed_structure.md`.
6. Validates constraints in `/validation_report.md`.
7. Executes a mapping only after explicit approval, saving `/final_mapping.json`.

## File Pipeline and Backends

The agent uses a single filesystem backend rooted at `DEEP_SCHOLAR_WORK_ROOT`.
These subfolders are used under that root:
- `/uploads/` -> `<work_root>/uploads`
- `/raw/` -> `<work_root>/raw`
- `/output/` -> `<work_root>/output`
- `/db/` -> `<work_root>/db`

## Custom Instructions

Custom instructions are defined in `src/deep_scholar/research_agent/prompts.py`:

| Instruction Set | Purpose |
| --- | --- |
| `FILE_RECONSTRUCTION_WORKFLOW_INSTRUCTIONS` | Deterministic workflow for intent, inventory, extraction, planning, validation, and execution. |
| `SUBAGENT_DELEGATION_INSTRUCTIONS` | Delegation limits and rules for file-analysis sub-agents. |
| `FILE_ANALYSIS_SUBAGENT_INSTRUCTIONS` | OCR, parsing, metadata extraction; returns structured JSON only. |
| `USER_INTENT_SUBAGENT_INSTRUCTIONS` | Infers task type, fields, grouping, and naming from `/user_intent.md`. |
| `STRUCTURE_PLANNING_SUBAGENT_INSTRUCTIONS` | Proposes a folder hierarchy and naming plan only. |
| `VALIDATION_SUBAGENT_INSTRUCTIONS` | Validates completeness, conflicts, and low-confidence fields. |

## Custom Tools

The file reconstruction agent adds the following tools beyond built-in deepagent tools:

| Tool Name | Description |
| --- | --- |
| `list_uploads` | Returns a JSON inventory of files in the work root's `uploads/` folder. |
| `read_text` | Reads text files with UTF-8 fallback. |
| `extract_pdf` | Extracts text from PDFs without OCR. |
| `ocr_pdf` | OCR for PDFs using the configured VLM backend (pdf2image + VLM). |
| `ocr_image` | OCR for images using the configured VLM backend. |
| `hash_file` | Computes file hashes for duplicate detection. |
| `apply_file_mapping` | Previews or executes file renames/moves from a JSON mapping. |
| `vectorize_text_tool` | Optional FAISS ingestion for semantic indexing. |

Note: `ocr_pdf` relies on `pdf2image`, which requires Poppler installed and available on PATH.

## Custom Model

By default, `deepagents` uses "claude-sonnet-4-5-20250929". You can customize this by passing any LangChain model object. See the Deepagents package README for more details.
