import json
import time
import ollama
from typing import Any, Callable
from configuration import BLUE, CYAN, GREEN, MAGENTA, OLLAMA_BASE_URL, RED, RESET, YELLOW
from uwazi_agents.experiments._common import (
    CAPABILITY_PROMPT,
    SEARCH_TOOL_DESCRIPTION,
    SEARCH_TOOL_NAME,
    UWAZI_FILTER_PROMPT,
    UWAZI_PROMPT,
    search_uwazi_entities,
)

TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": SEARCH_TOOL_NAME,
            "description": SEARCH_TOOL_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Free-text query (ignored when a date range is given).",
                    },
                    "template_name": {
                        "type": "string",
                        "description": "Uwazi template name, e.g. 'Resolution' or 'Document'.",
                    },
                    "language": {
                        "type": "string",
                        "description": "ISO 639-1 language code: 'en', 'fr', 'pt', 'es'.",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Lower bound, ISO date 'YYYY-MM-DD'.",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "Upper bound, ISO date 'YYYY-MM-DD'.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (1-100).",
                    },
                },
                "required": [],
            },
        },
    }
]

TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    SEARCH_TOOL_NAME: search_uwazi_entities,
}


def _dispatch(name: str, arguments: dict[str, Any]) -> str:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        return fn(**arguments)
    except Exception as exc:  # surface tool errors back to the model
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})


def run_agent(model: str, prompt: str, max_steps: int = 6) -> str:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

    for step in range(max_steps):
        response = client.chat(model=model, messages=messages, tools=TOOLS_SCHEMA)
        msg = response["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            return msg.get("content", "")

        for call in tool_calls:
            fn_name = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            if isinstance(args, str):
                args = json.loads(args)
            print(f"  [step {step}] {fn_name}({args})")
            result = _dispatch(fn_name, args)
            messages.append({"role": "tool", "name": fn_name, "content": result})

    return "[stopped: max_steps reached]"


def capability_check(model: str) -> None:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.chat(model=model, messages=[{"role": "user", "content": CAPABILITY_PROMPT}])
    print(f"{GREEN}{response["message"]["content"].strip()}{RESET}")


def load_model(model: str) -> None:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    client.chat(model=model, messages=[{"role": "user", "content": "Hello"}])


if __name__ == "__main__":
    models = ["gemma4:e2b", "nemotron-3-super:cloud"]
    for model in models:
        load_model(model)

        start_time = time.time()
        print(f"{BLUE}[native-ollama]{RESET} {YELLOW}Checking model:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{CAPABILITY_PROMPT}{RESET}")
        capability_check(model)
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(f"{BLUE}[native-ollama]{RESET} {YELLOW}Running Uwazi text search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_PROMPT}{RESET}")
        print(f"{GREEN}{run_agent(model, UWAZI_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(f"{BLUE}[native-ollama]{RESET} {YELLOW}Running Uwazi filtered search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_FILTER_PROMPT}{RESET}")
        print(f"{GREEN}{run_agent(model, UWAZI_FILTER_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)
        print("#" * 100)
