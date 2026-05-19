import time
import ollama
from smolagents import CodeAgent, LiteLLMModel, ToolCallingAgent, tool
from configuration import BLUE, CYAN, GREEN, OLLAMA_BASE_URL, RED, RESET, YELLOW
from uwazi_agents.experiments._common import (
    CAPABILITY_PROMPT,
    UWAZI_FILTER_PROMPT,
    UWAZI_PROMPT,
    search_uwazi_entities,
)


@tool
def search_uwazi(
    query: str | None = None,
    template_name: str | None = None,
    language: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10,
) -> str:
    """Search the Uwazi database. All arguments are optional.

    Args:
        query: Free-text search term (ignored when a date range is given).
        template_name: Uwazi template, e.g. 'Resolution' or 'Document'.
        language: ISO 639-1 language code: 'en', 'fr', 'pt', 'es'.
        date_from: Lower bound, ISO date 'YYYY-MM-DD'.
        date_to: Upper bound, ISO date 'YYYY-MM-DD'.
        limit: Maximum number of results to return (1-100).
    """
    return search_uwazi_entities(
        query=query,
        template_name=template_name,
        language=language,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


def build_model(model_name: str) -> LiteLLMModel:
    return LiteLLMModel(
        model_id=f"ollama_chat/{model_name}",
        api_base=OLLAMA_BASE_URL,
        temperature=1.0,
    )


def capability_check(model_name: str) -> None:
    model = build_model(model_name)
    out = model.generate([{"role": "user", "content": [{"type": "text", "text": CAPABILITY_PROMPT}]}])
    print(f"{GREEN}{out.content.strip() if hasattr(out, "content") else str(out).strip()}{RESET}")


def tool_calling_run(model_name: str, prompt: str = UWAZI_PROMPT) -> None:
    agent = ToolCallingAgent(tools=[search_uwazi], model=build_model(model_name))
    print(f"{GREEN}{agent.run(prompt)}{RESET}")


def code_agent_run(model_name: str, prompt: str = UWAZI_PROMPT) -> None:
    agent = CodeAgent(
        tools=[search_uwazi],
        model=build_model(model_name),
        additional_authorized_imports=["json"],
    )
    print(f"{GREEN}{agent.run(prompt)}{RESET}")


def load_model(model: str) -> None:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    client.chat(model=model, messages=[{"role": "user", "content": "Hello"}])


if __name__ == "__main__":
    models = ["gemma4:e2b", "nemotron-3-super:cloud"]
    for model in models:
        load_model(model)

        start_time = time.time()
        print(f"{BLUE}[smolagents]{RESET} {YELLOW}Checking model:{RESET} {RED}{model}{RESET}")
        capability_check(model)
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(
            f"{BLUE}[smolagents]{RESET} {YELLOW}Running Uwazi text search with {CYAN}ToolCallingAgent{RESET}:{RESET} {RED}{model}{RESET}"
        )
        tool_calling_run(model, UWAZI_PROMPT)
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(
            f"{BLUE}[smolagents]{RESET} {YELLOW}Running Uwazi filtered search with {CYAN}ToolCallingAgent{RESET}:{RESET} {RED}{model}{RESET}"
        )
        tool_calling_run(model, UWAZI_FILTER_PROMPT)
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(
            f"{BLUE}[smolagents]{RESET} {YELLOW}Running Uwazi text search with {CYAN}CodeAgent{RESET}:{RESET} {RED}{model}{RESET}"
        )
        code_agent_run(model, UWAZI_PROMPT)
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(
            f"{BLUE}[smolagents]{RESET} {YELLOW}Running Uwazi filtered search with {CYAN}CodeAgent{RESET}:{RESET} {RED}{model}{RESET}"
        )
        code_agent_run(model, UWAZI_FILTER_PROMPT)
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)
