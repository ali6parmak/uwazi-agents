
import time
import ollama
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from configuration import BLUE, CYAN, GREEN, MAGENTA, OLLAMA_BASE_URL, RED, RESET, YELLOW
from uwazi_agents.experiments._common import (
    SEARCH_TOOL_DESCRIPTION,
    UWAZI_FILTER_PROMPT,
    UWAZI_PROMPT,
    search_uwazi_entities,
)


class UwaziEntity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str | None = None
    shared_id: str | None = None
    title: str | None = None
    template: str | None = None
    language: str | None = None
    date: str | None = None

class SearchResult(BaseModel):
    mode: str
    count: int
    results: list[UwaziEntity]


def build_agent(model_name: str) -> Agent[None, SearchResult]:
    model = OpenAIChatModel(
        model_name=model_name,
        provider=OllamaProvider(base_url=f"{OLLAMA_BASE_URL}/v1"),
    )
    agent: Agent[None, SearchResult] = Agent(
        model=model,
        output_type=SearchResult,
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

def uwazi_run(model_name: str, prompt: str = UWAZI_PROMPT) -> SearchResult:
    agent = build_agent(model_name)
    result = agent.run_sync(prompt)
    return result.output

def load_model(model_name: str) -> None:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    client.chat(model=model_name, messages=[{"role": "user", "content": "Hello"}])

if __name__ == "__main__":
    models = ["nemotron-3-super:cloud"]

    for model in models:
        load_model(model)

        start_time = time.time()
        print(f"{BLUE}[pydantic-ai]{RESET} {YELLOW}Running Uwazi text search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_PROMPT}{RESET}")
        print(f"{GREEN}{uwazi_run(model, UWAZI_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*"*100)

        start_time = time.time()
        print(f"{BLUE}[pydantic-ai]{RESET} {YELLOW}Running Uwazi filtered search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_FILTER_PROMPT}{RESET}")
        print(f"{GREEN}{uwazi_run(model, UWAZI_FILTER_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*"*100)
        print("#"*100)
