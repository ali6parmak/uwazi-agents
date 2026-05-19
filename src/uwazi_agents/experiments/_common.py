import json
from datetime import date
from uwazi_agents.uwazi_example import search_by_text, search_with_filters

_EMPTY_SENTINELS = {"", "null", "none", "nil", "n/a", "na", "undefined"}
_LANGUAGE_ALIASES: dict[str, str] = {
    "en": "en",
    "english": "en",
    "fr": "fr",
    "french": "fr",
    "francais": "fr",
    "français": "fr",
    "pt": "pt",
    "portuguese": "pt",
    "portugues": "pt",
    "português": "pt",
    "es": "es",
    "spanish": "es",
    "espanol": "es",
    "español": "es",
}


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in _EMPTY_SENTINELS:
        return None
    return value.strip() if isinstance(value, str) else value


def _normalize_language(value: str | None, default: str = "en") -> str:
    v = _normalize_optional_str(value)
    if v is None:
        return default
    return _LANGUAGE_ALIASES.get(v.lower(), v.lower())


def _parse_date(value: str | None) -> date | None:
    v = _normalize_optional_str(value)
    if v is None:
        return None
    return date.fromisoformat(v)


def search_uwazi_entities(
    query: str | None = None,
    template_name: str | None = None,
    language: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 10,
) -> str:
    """Search Uwazi. All parameters are optional; pick whichever apply.

    Args:
        query: Free-text query. Used only when no date range is given.
        template_name: Uwazi template (e.g. "Resolution", "Document").
        language: ISO 639-1 language code ("en", "fr", "pt", "es").
        date_from: ISO date string ``YYYY-MM-DD`` for the lower bound.
        date_to:   ISO date string ``YYYY-MM-DD`` for the upper bound.
        limit: Max number of records to return (1-100).

    Returns:
        A JSON string with ``mode``, ``count``, ``results``, where each
        result entry has ``shared_id``, ``title``, ``template``, ``language``.
    """
    template_name = _normalize_optional_str(template_name)
    lang = _normalize_language(language)
    df_from = _parse_date(date_from)
    df_to = _parse_date(date_to)
    text_query = _normalize_optional_str(query)
    bounded_limit = max(1, min(int(limit or 10), 100))

    try:
        # Filter mode wins as soon as a date range or template is present:
        # search_by_text doesn't accept filters, so we'd have to drop them.
        if df_from is not None or df_to is not None or (template_name and not text_query):
            df = search_with_filters(
                template_name=template_name,
                language=lang,
                date_from=df_from,
                date_to=df_to,
                batch_size=bounded_limit,
            )
            mode = "filter"
        elif text_query:
            df = search_by_text(
                search_term="title:" + text_query,
                template_name=template_name,
                language=lang,
                batch_size=bounded_limit,
            )
            mode = "text"
        else:
            df = search_with_filters(language=lang, batch_size=bounded_limit)
            mode = "filter"
    except Exception as exc:
        # Surface clean errors back to the model so it can correct itself
        # instead of seeing a stack trace.
        return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    if df.empty:
        return json.dumps({"mode": mode, "count": 0, "results": []})

    # The two underlying helpers return slightly different column names
    # (search_by_text -> snake_case; entities_to_dataframe -> camelCase
    # plus a bunch of metadata). Normalize to a small stable shape so the
    # tool output looks identical across modes and stays cheap on tokens.
    df = df.rename(columns={"sharedId": "shared_id", "_id": "id"})
    keep = [c for c in ("id", "shared_id", "title", "template", "language", "date") if c in df.columns]
    records = df.head(bounded_limit)[keep].to_dict(orient="records")
    return json.dumps({"mode": mode, "count": len(records), "results": records}, default=str)


SEARCH_TOOL_NAME = "search_uwazi_entities"
SEARCH_TOOL_DESCRIPTION = (
    "Search the Uwazi database for entities. All arguments are optional; "
    "use as many as the user actually specifies.\n"
    "- query: free-text search term (used only when no date range is given).\n"
    "- template_name: Uwazi template such as 'Resolution' or 'Document'.\n"
    "- language: ISO 639-1 code ('en', 'fr', 'pt', 'es').\n"
    "- date_from / date_to: ISO dates 'YYYY-MM-DD'. Compute them yourself "
    "from phrases like 'last month of 2020'.\n"
    "Returns JSON with 'mode', 'count' and a 'results' list "
    "(shared_id, title, template, language)."
)


CAPABILITY_PROMPT = "In one sentence, describe what an AI agent is and why tool use matters."

UWAZI_PROMPT = "Find Uwazi entities that mention 'plan' and tell me how many you found " "and the title of the first one."

UWAZI_FILTER_PROMPT = (
    "I want to see all the documents that have Resolution template in "
    "French from 10 January 2020 to 18 May 2026. How many are there and "
    "what is the title of the first one?"
)
