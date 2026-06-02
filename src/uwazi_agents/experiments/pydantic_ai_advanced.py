import json
import time
import ollama
import pandas as pd
from dataclasses import dataclass, field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from configuration import BLUE, CYAN, GREEN, MAGENTA, OLLAMA_BASE_URL, RED, RESET, YELLOW
from uwazi_agents.uwazi_tools import (
    fetch_entities_dataframe,
    list_templates_summary,
    run_python_on_entities,
)


SYSTEM_PROMPT = (
    "You are an analyst with read-only access to a Uwazi document database. "
    "You can call these tools:\n"
    "  - list_templates(name=None): list templates (all, or one by name) "
    "with their properties. Cheap.\n"
    "  - fetch_entities(template_name=None, language='en', limit=10000): "
    "returns compact entity rows. Expensive when limit is large.\n"
    "  - python_exec(code, template_name=None, language='en', "
    "fetch_limit=10000): loads up to fetch_limit entities into a pandas "
    "DataFrame named 'df' and runs your Python. You MUST assign the "
    "final answer to a variable called 'result'. Use this for filtering, "
    "aggregating, or counting over result sets.\n"
    "\n"
    "Guidelines:\n"
    "- Compose tools rather than expecting a tool per question. For "
    "example, to count per template, pass template_name=None to "
    "python_exec and group `df` by the 'template' column, then map "
    "those template IDs back using list_templates.\n"
    "- The python_exec response includes a 'truncated' flag and "
    "'fetched_rows' so you can tell when fetch_limit was the cap; raise "
    "fetch_limit (max 10000) only if the question really needs more rows.\n"
    "- Only ask for as much data (limit/fetch_limit) as the question "
    "actually needs.\n"
    "- When you compute dates in prose, convert to ISO 'YYYY-MM-DD' "
    "strings before calling tools."
)


@dataclass
class UwaziDeps:
    last_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    last_query: dict = field(default_factory=dict)


def build_agent(model_name: str) -> Agent[UwaziDeps, str]:
    model = OpenAIChatModel(
        model_name=model_name,
        provider=OllamaProvider(base_url=f"{OLLAMA_BASE_URL}/v1"),
    )
    agent: Agent[UwaziDeps, str] = Agent(model=model, deps_type=UwaziDeps, system_prompt=SYSTEM_PROMPT)

    @agent.tool(name="list_templates")
    def _list_templates(ctx: RunContext[UwaziDeps], name: str | None = None) -> str:
        """List Uwazi templates with their properties.

        Args:
            name: Optional template name. If given, only that template
                  is returned (or an empty list if it doesn't exist).
        """

        params = f"{YELLOW}{name=}{RESET}"
        print(f"{CYAN}[list_templates]{RESET} tool called with the parameters: {params}")
        return json.dumps(list_templates_summary(name=name), default=str)

    @agent.tool(name="fetch_entities")
    def _fetch(
        ctx: RunContext[UwaziDeps],
        template_name: str | None = None,
        language: str = "en",
        limit: int = 10000,
    ) -> str:
        """Fetch compact entity rows (id, sharedId, title, template, language, creationDate).

        Args:
            template_name: Optional Uwazi template to restrict to.
            language: ISO 639-1 language code (default 'en').
            limit: Max number of rows (capped to 10000).
        """
        params = f"{YELLOW}{template_name=} {language=} {limit=}{RESET}"
        print(f"{CYAN}[fetch_entities]{RESET} tool called with the parameters: {params}")
        capped = max(1, min(int(limit), 10000))
        df = fetch_entities_dataframe(
            template_name=template_name, language=language, limit=capped
        )
        keep = [
            c
            for c in ("_id", "sharedId", "title", "template", "language", "creationDate")
            if c in df.columns
        ]

        ctx.deps.last_df = df
        ctx.deps.last_query = {
            "template_name": template_name,
            "language": language,
            "limit": limit,
        }

        return json.dumps(
            {
                "count": int(len(df)),
                "limit_used": capped,
                "results": df.loc[:, keep].to_dict(orient="records") if keep else [],
            },
            default=str,
        )

    @agent.tool(name="python_exec")
    def _python(
        ctx: RunContext[UwaziDeps],
        code: str,
        template_name: str | None = None,
        language: str = "en",
        fetch_limit: int = 10000,
    ) -> str:
        """Run analyst Python over a DataFrame ``df`` of fetched entities.

        Pre-loaded globals: ``df`` (pandas DataFrame), ``pd`` (pandas),
        ``re`` (regex), ``Counter`` (collections). The snippet MUST set
        a variable named ``result`` to the value you want to return.

        Args:
            code: The Python source to execute. Multiple lines are fine.
            template_name: Optional template name to scope ``df``.
            language: ISO 639-1 language code for the underlying fetch.
            fetch_limit: Max entities to pull into ``df`` (capped to 10000).
        """
        params = f"{YELLOW}\ncode:\n-------\n{code}\n-------\n {template_name=}, {language=}, {fetch_limit=}{RESET}"
        print(f"{CYAN}[_python_exec]{RESET} tool called with the parameters: {params}")
        capped = max(1, min(int(fetch_limit), 10000))
        try:
            out = run_python_on_entities(
                code=code,
                template_name=template_name,
                language=language,
                fetch_limit=capped,
            )
            return json.dumps(out, default=str)
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    return agent

PROMPTS: dict[str, str] = {
    "templates_list": (
        "List the templates in the database. For each, give me just the "
        "name and the number of (non-common) properties."
    ),
    "templates_lookup": (
        "Does a template called 'Resolution' exist? If so, what are its "
        "property names and types?"
    ),
    "scale_total": "How many entities are stored in total across all templates?",
    "scale_top_template": (
        "Which template has the most documents? Give me the top 3 with "
        "their counts (use the template names, not the IDs)."
    ),
    "custom_starts_with_c": (
        "How many entities have a title that starts with the letter 'C' (case-insensitive)."
    ),
    "custom_first_letter": (
        "What is the most common first letter of entity titles across "
        "the whole database, ignoring case? Return the top 5 letters "
        "with their counts."
    ),
}


def uwazi_run(model_name: str, prompt: str) -> str:
    agent = build_agent(model_name)
    deps = UwaziDeps()
    result = agent.run_sync(prompt, deps=deps)

    if not deps.last_df.empty:
        print(f"\n--- DataFrame ({len(deps.last_df)} rows) ---")
        print(deps.last_df.head(20))
        print(f"\n--- Last query: {deps.last_query} ---")

    return result.output.strip()


def load_model(model_name: str) -> None:
    ollama.Client(host=OLLAMA_BASE_URL).chat(
        model=model_name, messages=[{"role": "user", "content": "Hello"}]
    )


def _run_prompt(model: str, label: str, prompt: str) -> None:
    start = time.time()
    print(
        f"{BLUE}[pydantic-ai/advanced]{RESET} {YELLOW}{label}{RESET} "
        f"on {RED}{model}{RESET}"
    )
    print(f"{MAGENTA}{prompt}{RESET}")
    try:
        print(f"{GREEN}{uwazi_run(model, prompt)}{RESET}")
    except Exception as exc:
        print(f"{RED}error: {type(exc).__name__}: {exc}{RESET}")
    print(f"{CYAN}Time taken: {time.time() - start:.2f} seconds{RESET}")
    print("*" * 100)


if __name__ == "__main__":
    models = ["granite4.1:30b"]

    for model in models:
        load_model(model)
        for label, prompt in PROMPTS.items():
            _run_prompt(model, label, prompt)
        print("#" * 100)
