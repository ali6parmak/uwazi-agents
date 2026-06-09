import json
import time
import ollama
import pandas as pd
from dataclasses import dataclass, field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.ollama import OllamaProvider

from configuration import BLUE, CYAN, DARK_GRAY_BG, DARK_ORANGE_BG, GREEN, MAGENTA, OLLAMA_BASE_URL, RED, RESET, YELLOW
from uwazi_agents.uwazi_tools import (
    add_thesauri_values,
    create_entity,
    create_page,
    delete_entities,
    delete_pages_by_title,
    fetch_entities_dataframe,
    list_pages,
    list_templates_summary,
    list_thesauri,
    run_python_on_entities,
)

SYSTEM_PROMPT = (
    "You are an assistant managing a Uwazi document database. You have "
    "both read (analytics) and write (admin) tools.\n"
    "\n"
    "Read / analytics tools:\n"
    "  - list_templates(name=None): list templates (all, or one by name) "
    "with their properties. Cheap.\n"
    "  - fetch_entities(template_name=None, language='en', limit=10000): "
    "returns compact entity rows. Expensive when limit is large.\n"
    "  - python_exec(code, template_name=None, language='en', "
    "fetch_limit=10000): loads up to fetch_limit entities into a pandas "
    "DataFrame named 'df' and runs your Python. You MUST assign the "
    "final answer to a variable called 'result'. Use this for filtering, "
    "aggregating, or counting over result sets.\n"
    "  - list_thesauri(language='en'): list thesauri and their values.\n"
    "  - list_pages(language='en'): list pages with their titles and urls.\n"
    "\n"
    "Write / admin tools (these MODIFY the database, use deliberately):\n"
    "  - create_entity(title, template_name, language='en'): create one "
    "entity under an existing template.\n"
    "  - delete_entities(template_name=None, title=None, language='en'): "
    "delete entities by template and/or exact title. At least one filter "
    "is required.\n"
    "  - add_thesauri_values(thesauri_name, values, language='en'): append "
    "new labels to an existing thesaurus (existing values are kept).\n"
    "  - create_page(title, markdown=None, javascript=None, language='en'): "
    "create a page. Pass 'markdown' for a markdown/HTML body and/or "
    "'javascript' for a page with a script.\n"
    "  - delete_pages_by_title(title, language='en'): delete every page "
    "with that exact title.\n"
    "\n"
    "Guidelines:\n"
    "- Compose tools rather than expecting a tool per question. For "
    "example, to count per template, pass template_name=None to "
    "python_exec and group `df` by the 'template' column, then map "
    "those template IDs back using list_templates.\n"
    "- Before creating an entity or adding thesaurus values, confirm the "
    "target template/thesaurus exists with list_templates / list_thesauri.\n"
    "- Destructive tools (delete_entities, delete_pages_by_title) are "
    "irreversible. Only call them when the user clearly asked to delete, "
    "and always pass a specific filter.\n"
    "- The python_exec response includes a 'truncated' flag and "
    "'fetched_rows' so you can tell when fetch_limit was the cap; raise "
    "fetch_limit (max 10000) only if the question really needs more rows.\n"
    "- Only ask for as much data (limit/fetch_limit) as the question "
    "actually needs.\n"
    "- When you compute dates in prose, convert to ISO 'YYYY-MM-DD' "
    "strings before calling tools."
)


def _colorize_code_block(code: str) -> str:
    lines: list[str] = code.strip().split(sep="\n")
    width: int = max(len(line) for line in lines)
    colored_str: str = DARK_ORANGE_BG + " " * (width + 4) + RESET + "\n"

    for line in lines:
        padded: str = line.ljust(width)
        colored_str += DARK_ORANGE_BG + f"  {padded}  " + RESET + "\n"

    colored_str += DARK_ORANGE_BG + " " * (width + 4) + RESET + "\n"
    return colored_str


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
        df = fetch_entities_dataframe(template_name=template_name, language=language, limit=capped)
        keep = [c for c in ("_id", "sharedId", "title", "template", "language", "creationDate") if c in df.columns]

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
        params: str = f"{YELLOW}\ncode:{RESET}\n{_colorize_code_block(code)}\n"
        params += f"{YELLOW}{template_name=}, {language=}, {fetch_limit=}{RESET}"
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

    @agent.tool(name="list_thesauri")
    def _list_thesauri(ctx: RunContext[UwaziDeps], language: str = "en") -> str:
        """List the Uwazi thesauri (controlled vocabularies) and their values.

        Args:
            language: ISO 639-1 language code (default 'en').
        """
        print(f"{CYAN}[list_thesauri]{RESET} tool called with the parameters: {YELLOW}{language=}{RESET}")
        return json.dumps(list_thesauri(language=language), default=str)

    @agent.tool(name="list_pages")
    def _list_pages(ctx: RunContext[UwaziDeps], language: str = "en") -> str:
        """List Uwazi pages (title, url, and whether they have markdown/javascript).

        Args:
            language: ISO 639-1 language code (default 'en').
        """
        print(f"{CYAN}[list_pages]{RESET} tool called with the parameters: {YELLOW}{language=}{RESET}")
        return json.dumps(list_pages(language=language), default=str)

    @agent.tool(name="create_entity")
    def _create_entity(
        ctx: RunContext[UwaziDeps],
        title: str,
        template_name: str,
        language: str = "en",
    ) -> str:
        """Create a single entity under an existing template.

        Args:
            title: The entity's title (its primary name).
            template_name: Name of an existing template.
            language: ISO 639-1 language code (default 'en').
        """
        params = f"{YELLOW}{title=} {template_name=} {language=}{RESET}"
        print(f"{CYAN}[create_entity]{RESET} tool called with the parameters: {params}")
        try:
            return json.dumps(create_entity(title=title, template_name=template_name, language=language), default=str)
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    @agent.tool(name="delete_entities")
    def _delete_entities(
        ctx: RunContext[UwaziDeps],
        template_name: str | None = None,
        title: str | None = None,
        language: str = "en",
    ) -> str:
        """Delete entities by template and/or exact title (at least one required).

        Args:
            template_name: Restrict deletion to this template.
            title: Restrict deletion to entities with this exact title.
            language: ISO 639-1 language code (default 'en').
        """
        params = f"{YELLOW}{template_name=} {title=} {language=}{RESET}"
        print(f"{CYAN}[delete_entities]{RESET} tool called with the parameters: {params}")
        try:
            return json.dumps(delete_entities(template_name=template_name, title=title, language=language), default=str)
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    @agent.tool(name="add_thesauri_values")
    def _add_thesauri_values(
        ctx: RunContext[UwaziDeps],
        thesauri_name: str,
        values: list[str],
        language: str = "en",
    ) -> str:
        """Append new labels to an existing thesaurus (existing values are kept).

        Args:
            thesauri_name: Name of an existing thesaurus.
            values: Labels to add.
            language: ISO 639-1 language code (default 'en').
        """
        params = f"{YELLOW}{thesauri_name=} {values=} {language=}{RESET}"
        print(f"{CYAN}[add_thesauri_values]{RESET} tool called with the parameters: {params}")
        try:
            return json.dumps(
                add_thesauri_values(thesauri_name=thesauri_name, values=values, language=language), default=str
            )
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    @agent.tool(name="create_page")
    def _create_page(
        ctx: RunContext[UwaziDeps],
        title: str,
        markdown: str | None = None,
        javascript: str | None = None,
        language: str = "en",
    ) -> str:
        """Create a page with markdown content and/or a javascript script.

        Args:
            title: The page title.
            markdown: Markdown/HTML body for the page.
            javascript: JavaScript stored on the page (the UI "Javascript" tab).
            language: ISO 639-1 language code (default 'en').
        """
        params = f"{YELLOW}{title=} markdown={bool(markdown)} javascript={bool(javascript)} {language=}{RESET}"
        print(f"{CYAN}[create_page]{RESET} tool called with the parameters: {params}")
        try:
            return json.dumps(
                create_page(title=title, markdown=markdown, javascript=javascript, language=language), default=str
            )
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    @agent.tool(name="delete_pages_by_title")
    def _delete_pages_by_title(
        ctx: RunContext[UwaziDeps],
        title: str,
        language: str = "en",
    ) -> str:
        """Delete every page whose title matches exactly.

        Args:
            title: The exact page title to delete.
            language: ISO 639-1 language code (default 'en').
        """
        params = f"{YELLOW}{title=} {language=}{RESET}"
        print(f"{CYAN}[delete_pages_by_title]{RESET} tool called with the parameters: {params}")
        try:
            return json.dumps(delete_pages_by_title(title=title, language=language), default=str)
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    return agent


PROMPTS: dict[str, str] = {
    "templates_list": (
        "List the templates in the database. For each, give me just the " "name and the number of (non-common) properties."
    ),
    "templates_lookup": ("Does a template called 'Resolution' exist? If so, what are its " "property names and types?"),
    "scale_total": "How many entities are stored in total across all templates?",
    "scale_top_template": (
        "Which template has the most documents? Give me the top 3 with "
        "their counts (use the template names, not the IDs)."
    ),
    "custom_starts_with_c": ("How many entities have a title that starts with the letter 'C' (case-insensitive)."),
    "custom_first_letter": (
        "What is the most common first letter of entity titles across "
        "the whole database, ignoring case? Return the top 5 letters "
        "with their counts."
    ),
    "thesauri_list": ("List the thesauri in the database and, for each, how many values " "it currently has."),
    "thesauri_add_values": (
        "Add the values 'Malawi', 'Zambia' and 'Mozambique' to the "
        "'Country' thesaurus. Skip any that already exist and tell me which "
        "ones were actually added."
    ),
    "thesauri_add_existing_values": (
        "Add the values 'Malawi', 'Zambia', 'Somalia' and 'Mozambique' to the "
        "'Country' thesaurus. Skip any that already exist and tell me which "
        "ones were actually added."
    ),
    "entity_create": (
        "Create a new entity titled 'Test Entity' under the 'BarEntity' " "template, then confirm its sharedId."
    ),
    "multiple_entity_create": (
        "Create 5 new entities titled 'Test Entity' under the 'BarEntity' " "template, then confirm its sharedId."
    ),
    "entity_delete": (
        "Delete every entity in the 'BarEntity' template whose title is " "'Test Entity', and report how many were removed."
    ),
    "pages_list": "List the pages in the database with their titles and urls.",
    "page_create_markdown": (
        "Create a page titled 'Agent Notes' whose markdown body is a level-1 "
        "heading 'Agent Notes' followed by the sentence 'Created by the "
        "Uwazi agent.', then give me its url."
    ),
    "page_create_javascript": (
        "Create a page titled 'Agent Script' that has the javascript "
        "console.log('hello from the agent'); and a short markdown intro, "
        "then give me its url."
    ),
    "page_delete": "Delete every page titled 'Agent Notes'.",
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
    ollama.Client(host=OLLAMA_BASE_URL).chat(model=model_name, messages=[{"role": "user", "content": "Hello"}])


def _run_prompt(model: str, label: str, prompt: str) -> None:
    start = time.time()
    print(f"{BLUE}[pydantic-ai/advanced]{RESET} {YELLOW}{label}{RESET} " f"on {RED}{model}{RESET}")
    print(f"{MAGENTA}{prompt}{RESET}")
    try:
        print(f"{GREEN}{uwazi_run(model, prompt)}{RESET}")
    except Exception as exc:
        print(f"{RED}error: {type(exc).__name__}: {exc}{RESET}")
    print(f"{CYAN}Time taken: {time.time() - start:.2f} seconds{RESET}")
    print(DARK_GRAY_BG + "*" * 100 + RESET)


if __name__ == "__main__":
    models: list[str] = ["deepseek-v4-flash:cloud"]

    for model in models:
        load_model(model_name=model)
        for label, prompt in PROMPTS.items():
            _run_prompt(model, label, prompt)
        print("#" * 100)
