import os

os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"
os.environ["CREWAI_TRACING_ENABLED"] = "false"
os.environ["OTEL_SDK_DISABLED"] = "true"
os.environ["OTEL_TRACES_EXPORTER"] = "none"
os.environ["OTEL_METRICS_EXPORTER"] = "none"
os.environ["OTEL_LOGS_EXPORTER"] = "none"

import time
from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import BaseTool
import ollama
from pydantic import BaseModel, Field

from configuration import BLUE, CYAN, GREEN, MAGENTA, OLLAMA_BASE_URL, RED, RESET, YELLOW
from uwazi_agents.experiments._common import (
    CAPABILITY_PROMPT,
    SEARCH_TOOL_DESCRIPTION,
    UWAZI_FILTER_PROMPT,
    UWAZI_PROMPT,
    search_uwazi_entities,
)


class _SearchArgs(BaseModel):
    query: str | None = Field(default=None, description="Free-text query (skipped when a date range is given).")
    template_name: str | None = Field(default=None, description="Uwazi template, e.g. 'Resolution' or 'Document'.")
    language: str | None = Field(default=None, description="ISO 639-1 language code: 'en', 'fr', 'pt', 'es'.")
    date_from: str | None = Field(default=None, description="Lower bound, ISO date 'YYYY-MM-DD'.")
    date_to: str | None = Field(default=None, description="Upper bound, ISO date 'YYYY-MM-DD'.")
    limit: int = Field(default=10, description="Maximum number of results (1-100).")


class UwaziSearchTool(BaseTool):
    name: str = "search_uwazi_entities"
    description: str = SEARCH_TOOL_DESCRIPTION
    args_schema: type[BaseModel] = _SearchArgs

    def _run(
        self,
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


def build_llm(model_name: str) -> LLM:
    return LLM(model=f"ollama_chat/{model_name}", base_url=OLLAMA_BASE_URL)


def capability_check(model_name: str) -> str:
    llm = build_llm(model_name)
    return llm.call([{"role": "user", "content": CAPABILITY_PROMPT}]).strip()


def crew_run(model_name: str, prompt: str = UWAZI_PROMPT) -> str:
    researcher = Agent(
        role="Uwazi Researcher",
        goal="Answer questions about documents stored in Uwazi.",
        backstory=(
            "A meticulous researcher who always uses the Uwazi search tool "
            "before guessing about the contents of the database. When the "
            "user gives dates in prose, compute ISO 'YYYY-MM-DD' bounds first."
        ),
        tools=[UwaziSearchTool()],
        llm=build_llm(model_name),
        allow_delegation=False,
        verbose=False,
    )
    task = Task(
        description=prompt,
        expected_output="A short paragraph with the count and the first title.",
        agent=researcher,
    )
    crew = Crew(agents=[researcher], tasks=[task], process=Process.sequential, verbose=False)
    return crew.kickoff()


def load_model(model: str) -> None:
    client = ollama.Client(host=OLLAMA_BASE_URL)
    client.chat(model=model, messages=[{"role": "user", "content": "Hello"}])


if __name__ == "__main__":
    models = ["gemma4:e2b", "nemotron-3-super:cloud"]
    for model in models:
        load_model(model)

        start_time = time.time()
        print(f"{BLUE}[crewai]{RESET} {YELLOW}Checking model:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{CAPABILITY_PROMPT}{RESET}")
        print(f"{GREEN}{capability_check(model)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(f"{BLUE}[crewai]{RESET} {YELLOW}Running Uwazi text search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_PROMPT}{RESET}")
        print(f"{GREEN}{crew_run(model, UWAZI_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)

        start_time = time.time()
        print(f"{BLUE}[crewai]{RESET} {YELLOW}Running Uwazi filtered search:{RESET} {RED}{model}{RESET}")
        print(f"{MAGENTA}{UWAZI_FILTER_PROMPT}{RESET}")
        print(f"{GREEN}{crew_run(model, UWAZI_FILTER_PROMPT)}{RESET}")
        print(f"{CYAN}Time taken: {time.time() - start_time:.2f} seconds{RESET}")
        print("*" * 100)
        print("#" * 100)
