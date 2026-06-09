# Uwazi Agents

Agentic workflows for [Uwazi](https://github.com/huridocs/uwazi) — an open-source document management platform by HURIDOCS. This project uses LLM-powered agents to programmatically query and manage Uwazi entities, templates, thesauri, and pages.

## Motivation

The goal is to replace manual data-entry and admin workflows in Uwazi with natural-language-driven agents. Instead of clicking through the UI to create templates, add thesaurus values, or run analytics across entities, you can tell an agent what you need and let it figure out the API calls.

## Current focus: pydantic-ai

After experimenting with several frameworks, development is now focused on **[pydantic-ai](https://ai.pydantic.dev/)**. It offers:

- First-class typed tool definitions via plain Python functions
- Structured output via Pydantic models
- Clean agent dependency injection (`RunContext`)
- Lightweight — no heavy abstractions, no telemetry noise
- Excellent DX with type hints and IDE support

The main pydantic-ai experiments:

| File | Description |
|---|---|
| `src/uwazi_agents/experiments/pydantic_ai_chat.py` | Basic agent with a single search tool (text + filter modes) |
| `src/uwazi_agents/experiments/pydantic_ai_structured_output.py` | Same agent but returns typed `SearchResult` model instead of raw text |
| `src/uwazi_agents/experiments/pydantic_ai_advanced.py` | Full-featured agent with read/write tools: templates, entities, thesauri, pages, and a `python_exec` tool for analytics over pandas DataFrames |

## Earlier framework experiments

Before settling on pydantic-ai, the following were tested for comparison:

| Framework | Experiment | Notes |
|---|---|---|
| **[smolagents](https://github.com/huggingface/smolagents)** (Hugging Face) | `smolagents_chat.py`, `run_uwazi_agent.py` | Tested both `ToolCallingAgent` and `CodeAgent`. CodeAgent writes & executes Python in a sandbox. Solid but heavier than needed. `run_uwazi_agent.py` is the project's current main entry point. |
| **[crewai](https://github.com/crewAIInc/crewAI)** | `crewai_chat.py` | Multi-agent orchestration framework. Functional but brought a lot of overhead (telemetry, complex abstractions) for what is ultimately a single-agent use case. |
| **Native Ollama** | `native_ollama_chat.py` | Raw tool-use loop via the ollama Python client with a manual dispatch table. Good for understanding the protocol, not ergonomic for real use. |

## Project structure

```
uwazi-agents/
├── run_uwazi_agent.py              # Main entry point (smolagents CodeAgent)
├── requirements.txt                # Dependencies
├── dev-requirements.txt            # Dev deps (black)
├── justfile                        # Formatter shortcut
├── src/
│   ├── configuration.py            # Environment-based configuration
│   ├── uwazi_agents/               # Current package
│   │   ├── uwazi_tools.py          # Core Uwazi tool implementations
│   │   ├── uwazi_example.py        # Example helpers (search, etc.)
│   │   ├── check_uwazi.py          # Ad-hoc scripts for testing the API
│   │   ├── seed_entities.py        # Seed/import scripts
│   │   ├── check_uwazi_pages.py    # Page inspection helpers
│   │   └── experiments/            # Framework comparison experiments
│   │       ├── pydantic_ai_chat.py
│   │       ├── pydantic_ai_structured_output.py
│   │       ├── pydantic_ai_advanced.py
│   │       ├── smolagents_chat.py
│   │       ├── crewai_chat.py
│   │       ├── native_ollama_chat.py
│   │       └── _common.py          # Shared search logic & prompts
│   └── uwazi_agents_v1/            # Earlier iteration (smolagents + domain models)
│       ├── config.py
│       ├── chaining_agents.py
│       ├── create_template.py
│       ├── domain/
│       │   ├── Template.py
│       │   ├── TemplateProperty.py
│       │   └── PropertyType.py
│       └── use_cases/
│           ├── uwazi_agent_interface.py
│           └── file_use_case.py
```

## Core capabilities

Through the pydantic-ai advanced agent (`pydantic_ai_advanced.py`), the following Uwazi operations are available as agent tools:

**Read / analytics** — `list_templates`, `fetch_entities`, `python_exec` (analytics over pandas DataFrames loaded from Uwazi), `list_thesauri`, `list_pages`

**Write / admin** — `create_entity`, `delete_entities`, `add_thesauri_values`, `create_page`, `delete_pages_by_title`

The `python_exec` tool is particularly powerful: it fetches entities into a `pandas.DataFrame` and lets the agent run arbitrary Python for counting, grouping, filtering — anything that doesn't have a dedicated endpoint.

## Getting started

```bash
# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Required environment variables:**

| Variable | Default | Description |
|---|---|---|
| `UWAZI_URL` | `http://localhost:3000` | Uwazi instance URL |
| `UWAZI_USER` | `admin` | Uwazi username |
| `UWAZI_PASSWORD` | `change this password now` | Uwazi password |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server URL |
| `GOOGLE_API_KEY` | — | Required when using Gemini models |

**Run a pydantic-ai experiment:**

```bash
python -m uwazi_agents.experiments.pydantic_ai_chat
```

**Run the main entry point (smolagents-based):**

```bash
python run_uwazi_agent.py
```

## Key dependencies

- **pydantic-ai** — agent framework (current focus)
- **smolagents** — agent framework used by the main entry point
- **crewai** — multi-agent framework (evaluated)
- **ollama** — local LLM serving
- **python_uwazi_API** — HURIDOCS' Python client for the Uwazi API
- **pandas** — data analytics in agent tools

## Model support

The experiments support both local models (via Ollama) and cloud models (via LiteLLM or direct API):

- **Local**: `gemma4:e2b`, `qwen2.5-coder:14b`, `gemma3:12b`
- **Cloud**: `gemini/gemini-2.5-flash`, `gemini/gemini-2.5-pro`, `deepseek-v4-flash:cloud`