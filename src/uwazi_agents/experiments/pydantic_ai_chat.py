import time
import ollama
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from configuration import BLUE, CYAN, GREEN, MAGENTA, OLLAMA_BASE_URL, RED, RESET, YELLOW
from uwazi_agents.experiments._common import (
    CAPABILITY_PROMPT,
    SEARCH_TOOL_DESCRIPTION,
    UWAZI_FILTER_PROMPT,
    UWAZI_PROMPT,
    search_uwazi_entities,
)


def build_agent(model_name: str) -> Agent[None, str]:
    model = OpenAIChatModel(
        model_name=model_name,
        provider=OllamaProvider(base_url=f"{OLLAMA_BASE_URL}/v1"),
    )
    agent: Agent[None, str] = Agent(
        model=model,
        system_prompt=(
            "You are an assistant with access to a Uwazi database via tools. "
            "Prefer calling tools over guessing when the user asks about "
            "stored documents or entities. When the user describes dates in "
            "prose (e.g. 'last month of 2020'), compute the bounds yourself "
            "and pass them as ISO 'YYYY-MM-DD' strings."
        ),
    )

    @agent.tool(name="search_uwazi_entities", description=SEARCH_TOOL_DESCRIPTION)
    def _search(
        ctx: RunContext[None],
        query: str | None = None,
        template_name: str | None = None,
        language: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 10,
    ) -> str:
        return search_uwazi_entities(
            query=query,
            template_name=template_name,
            language=language,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )

    return agent


def capability_check(model_name: str) -> str:
    agent = build_agent(model_name)
    result = agent.run_sync(CAPABILITY_PROMPT)
    return result.output.strip()


def uwazi_run(model_name: str, prompt: str = UWAZI_PROMPT) -> str:
    agent = build_agent(model_name)
    result = agent.run_sync(prompt)
    return result.output.strip()


def load_model(model_name: str) -> None:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    client.chat(model=model_name, messages=[{"role": "user", "content": "Hello"}])


if __name__ == "__main__":
    models = ["gemma4:e2b", "nemotron-3-super:cloud"]

    for model in models:
        load_model(model)

        start_time = time.time()
        print(f"{BLUE}[pydantic-ai]{RESET} {YELLOW}Checking model:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{CAPABILITY_PROMPT}{RESET}")
        print(f"{GREEN}{capability_check(model)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(f"{BLUE}[pydantic-ai]{RESET} {YELLOW}Running Uwazi text search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_PROMPT}{RESET}")
        print(f"{GREEN}{uwazi_run(model, UWAZI_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(f"{BLUE}[pydantic-ai]{RESET} {YELLOW}Running Uwazi filtered search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_FILTER_PROMPT}{RESET}")
        print(f"{GREEN}{uwazi_run(model, UWAZI_FILTER_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)
        print("#" * 100)
