"""Reusable Uwazi building blocks for agents.

These helpers are deliberately independent of any agent framework. They
expose Uwazi's templates, counts, and entity fetches behind small,
token-cheap signatures, plus an ``exec`` sandbox so a model can write
custom pandas code over a pre-loaded DataFrame instead of trying to
reason about thousands of rows in its context window.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import date
from functools import lru_cache
from typing import Any

import pandas as pd
from uwazi_api.client import UwaziClient
from uwazi_api.domain.search_filters import DateRange, SearchFilters

from configuration import UWAZI_PASSWORD, UWAZI_URL, UWAZI_USER

_OPEN_PAST = date(1900, 1, 1)
_OPEN_FUTURE = date(2100, 1, 1)


@lru_cache(maxsize=1)
def client() -> UwaziClient:
    """Authenticated client. Cached because login is a real HTTP round-trip."""
    return UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)


def list_templates_summary(name: str | None = None) -> list[dict[str, Any]]:
    """Return compact metadata for templates.

    Args:
        name: If given, return only the template whose ``name`` matches
            (empty list when nothing matches). Otherwise return all
            templates known to the instance.

    Returns:
        Each entry: ``{id, name, color, properties, common_properties}``
        where ``properties`` is a list of ``{name, label, type, filter}``.
    """
    c = client()
    if name:
        t = c.templates.get_by_name(name)
        templates = [t] if t is not None else []
    else:
        templates = c.templates.get()
    return [
        {
            "id": t.id,
            "name": t.name,
            "color": t.color,
            "properties": [
                {"name": p.name, "label": p.label, "type": str(p.type), "filter": p.filter}
                for p in t.properties
            ],
            "common_properties": [
                {"name": p.name, "label": p.label, "type": str(p.type)}
                for p in t.common_properties
            ],
        }
        for t in templates
    ]


def fetch_entities_dataframe(
    template_name: str | None = None,
    language: str = "en",
    limit: int = 200,
    date_from: str | None = None,
    date_to: str | None = None,
    page_size: int = 300,
) -> pd.DataFrame:
    """Fetch up to ``limit`` entities into a single DataFrame.

    Pagination is handled here so the caller can ask for 10k rows
    without having to know about Uwazi's batch limits.
    """
    filters = SearchFilters()
    if date_from is not None or date_to is not None:
        filters.add(
            "date",
            DateRange(
                from_=date.fromisoformat(date_from) if date_from else _OPEN_PAST,
                to=date.fromisoformat(date_to) if date_to else _OPEN_FUTURE,
            ),
        )

    frames: list[pd.DataFrame] = []
    fetched = 0
    while fetched < limit:
        batch = min(page_size, limit - fetched)
        df = client().search.search_by_filter_to_dataframe(
            filters=filters,
            template_name=template_name,
            language=language,
            start_from=fetched,
            batch_size=batch,
        )
        if df is None or df.empty:
            break
        frames.append(df)
        fetched += len(df)
        # Short page -> we've reached the end of the result set.
        if len(df) < batch:
            break

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# Builtins that are safe to expose to agent-authored code. We strip
# things like ``open`` / ``__import__`` so the model can't poke at the
# filesystem or pull in network libraries by accident.
_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _serialize_result(value: Any, head: int = 200) -> Any:
    """Render a Python value into something JSON-friendly and bounded.

    DataFrames/Series get truncated so a small ``result = df`` from the
    model doesn't accidentally dump 10k rows back into the LLM context.
    """
    if isinstance(value, pd.DataFrame):
        truncated = len(value) > head
        return {
            "columns": list(value.columns),
            "rows": value.head(head).to_dict(orient="records"),
            "truncated": truncated,
            "row_count": int(len(value)),
        }
    if isinstance(value, pd.Series):
        truncated = len(value) > head
        return {
            "data": value.head(head).to_dict(),
            "truncated": truncated,
            "length": int(len(value)),
        }
    if isinstance(value, (set, frozenset)):
        return sorted(value, key=str)
    if hasattr(value, "tolist") and not isinstance(value, (str, bytes)):
        try:
            return value.tolist()
        except Exception:
            return repr(value)
    return value


def run_python_on_entities(
    code: str,
    template_name: str | None = None,
    language: str = "en",
    fetch_limit: int = 5000,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict[str, Any]:
    """Fetch a DataFrame and run agent-authored Python over it.

    The supplied code must assign its answer to a variable named
    ``result``. Available names while it runs:

    - ``df``  : pandas DataFrame of the fetched entities.
    - ``pd``  : pandas module.
    - ``re``  : standard library regex module.
    - ``Counter`` : ``collections.Counter``.

    Returns a dict with the number of rows that were loaded, the type
    of the result, and a JSON-friendly serialization of the value.
    """
    df = fetch_entities_dataframe(
        template_name=template_name,
        language=language,
        limit=fetch_limit,
        date_from=date_from,
        date_to=date_to,
    )

    namespace: dict[str, Any] = {
        "__builtins__": _SAFE_BUILTINS,
        "df": df,
        "pd": pd,
        "re": re,
        "Counter": Counter,
    }
    exec(compile(code, "<agent-code>", "exec"), namespace)

    result = namespace.get("result")
    return {
        "fetched_rows": int(len(df)),
        "columns": list(df.columns),
        "result_type": type(result).__name__,
        "result": _serialize_result(result),
    }


__all__ = [
    "client",
    "list_templates_summary",
    "fetch_entities_dataframe",
    "run_python_on_entities",
]
