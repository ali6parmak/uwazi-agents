"""Reusable Uwazi building blocks for agents.

These helpers are deliberately independent of any agent framework. They
expose Uwazi's templates, counts, and entity fetches behind small,
token-cheap signatures, plus an ``exec`` sandbox so a model can write
custom pandas code over a pre-loaded DataFrame instead of trying to
reason about thousands of rows in its context window.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from uwazi_api.client import UwaziClient
from uwazi_api.domain.entity import Entity
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


def create_entity(
    title: str,
    template_name: str,
    language: str = "en",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a single entity under ``template_name``.

    Args:
        title: The entity title (its primary, human-readable name).
        template_name: Name of an existing template (see
            ``list_templates_summary``). Resolved to its id internally.
        language: ISO 639-1 language code the entity is created in.
        metadata: Optional raw Uwazi metadata mapping. Most callers can
            leave this empty and only set a title.

    Returns:
        ``{shared_id, title, template, language}`` for the new entity.
    """
    c = client()
    template = c.templates.get_by_name(template_name)
    if template is None:
        raise ValueError(
            f"No template named {template_name!r}. "
            "Call list_templates to see the valid names."
        )

    entity = Entity(
        title=title,
        template=template.id,
        language=language,
        metadata=metadata or {},
    )
    shared_id = c.entities.upload(entity=entity, language=language)
    return {
        "shared_id": shared_id,
        "title": title,
        "template": template_name,
        "language": language,
    }


def delete_entities(
    template_name: str | None = None,
    title: str | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Delete entities matching a template and/or an exact title.

    At least one of ``template_name`` / ``title`` is required: this guard
    prevents an accidental "delete every entity in the database" call.

    Args:
        template_name: Restrict deletion to entities of this template.
        title: Restrict deletion to entities whose title matches exactly.
        language: ISO 639-1 language code used while looking entities up.

    Returns:
        ``{deleted_count, titles}`` describing what was removed.
    """
    if not template_name and not title:
        raise ValueError(
            "Provide template_name and/or title; refusing to delete every "
            "entity in the database."
        )

    c = client()
    entities = c.entities.get(
        start_from=0,
        batch_size=9999,
        template_name=template_name,
        language=language,
    )
    if title is not None:
        entities = [e for e in entities if (e.title or "") == title]

    matched = [e for e in entities if e.shared_id]
    shared_ids = [e.shared_id for e in matched]
    if shared_ids:
        c.entities.delete_entities(shared_ids=shared_ids)

    return {
        "deleted_count": len(shared_ids),
        "titles": [e.title for e in matched],
    }


def _thesauri_rows(language: str = "en") -> list[dict[str, Any]]:
    """Raw ``/api/thesauris`` rows, including type and value ids.

    The typed ``client().thesauris`` repository drops the ``type`` field,
    but we need it to tell real thesauri apart from the relationship
    pick-lists Uwazi also returns from this endpoint.
    """
    http = client().thesauris.http
    response = http.request_adapter.get(
        url=f"{http.url}/api/thesauris",
        headers=http.headers,
        cookies={"locale": language},
    )
    response.raise_for_status()
    return json.loads(response.content.decode("utf-8")).get("rows", [])


def list_thesauri(language: str = "en") -> list[dict[str, Any]]:
    """List the real thesauri (Settings → Thesauri) with their values.

    Template relationship pick-lists (``type == "template"``) are filtered
    out so this matches what an editor sees in the Uwazi UI.

    Returns:
        Each entry: ``{id, name, values}`` where ``values`` is a list of
        label strings.
    """
    return [
        {
            "id": row.get("_id"),
            "name": row.get("name"),
            "values": [v.get("label") for v in row.get("values", [])],
        }
        for row in _thesauri_rows(language)
        if row.get("type") != "template"
    ]


def add_thesauri_values(
    thesauri_name: str,
    values: list[str],
    language: str = "en",
) -> dict[str, Any]:
    """Append new labels to an existing thesaurus, keeping current ones.

    Uwazi's save endpoint replaces the whole value list, so we merge the
    existing values with the requested additions before posting. Values
    already present (by label) are skipped.

    Args:
        thesauri_name: Name of an existing thesaurus (see ``list_thesauri``).
        values: Labels to add.
        language: ISO 639-1 language code.

    Returns:
        ``{thesaurus, added, total_values}`` (``added`` lists only the
        labels that were genuinely new).
    """
    match = next(
        (
            r
            for r in _thesauri_rows(language)
            if r.get("name") == thesauri_name and r.get("type") != "template"
        ),
        None,
    )
    if match is None:
        raise ValueError(
            f"No thesaurus named {thesauri_name!r}. "
            "Call list_thesauri to see the valid names."
        )

    existing = {
        v["label"]: v["id"]
        for v in match.get("values", [])
        if "label" in v and "id" in v
    }
    new_values = {v: v for v in values if v not in existing}
    if not new_values:
        return {"thesaurus": thesauri_name, "added": [], "total_values": len(existing)}

    merged = {**existing, **new_values}
    client().thesauris.add_value(
        thesauri_id=match["_id"],
        thesauri_values=merged,
        language=language,
    )
    return {
        "thesaurus": thesauri_name,
        "added": list(new_values),
        "total_values": len(merged),
    }


def _page_slug(title: str) -> str:
    """Mirror Uwazi's public page URLs, e.g. ``ExamplePage`` -> ``example-page``."""
    spaced = re.sub(r"(?<!^)(?=[A-Z])", "-", title.strip())
    return re.sub(r"[^a-zA-Z0-9]+", "-", spaced).strip("-").lower()


def page_url(page: dict[str, Any], base_url: str = UWAZI_URL) -> str:
    """Public URL for a page dict returned by the pages endpoint."""
    base = base_url.rstrip("/")
    return f"{base}/page/{page['sharedId']}/{_page_slug(page['title'])}"


def fetch_pages(language: str = "en") -> list[dict[str, Any]]:
    """Raw ``/api/pages`` rows for the given language."""
    http = client().thesauris.http
    response = http.request_adapter.get(
        url=f"{http.url}/api/pages",
        headers=http.headers,
        cookies={"locale": language},
    )
    response.raise_for_status()
    return json.loads(response.content.decode("utf-8"))


def list_pages(language: str = "en") -> list[dict[str, Any]]:
    """List pages as compact summaries (no full body, to stay token-cheap).

    Returns:
        Each entry: ``{shared_id, title, language, url, has_markdown,
        has_javascript}``.
    """
    summaries = []
    for page in fetch_pages(language):
        metadata = page.get("metadata") or {}
        summaries.append(
            {
                "shared_id": page.get("sharedId"),
                "title": page.get("title"),
                "language": page.get("language"),
                "url": page_url(page),
                "has_markdown": bool(metadata.get("content")),
                "has_javascript": bool(metadata.get("script")),
            }
        )
    return summaries


def create_page(
    title: str,
    markdown: str | None = None,
    javascript: str | None = None,
    *,
    markdown_path: str | Path | None = None,
    language: str = "en",
    entity_view: bool = False,
) -> dict[str, Any]:
    """Create a Settings → Pages entry via ``POST /api/pages``.

    A page always carries markdown/HTML ``content`` and may additionally
    carry a ``script`` (the UI's "Javascript" tab). Supply at least one of
    ``markdown`` / ``markdown_path`` / ``javascript``.

    Args:
        title: Page title (also used to build the public slug).
        markdown: Markdown/HTML body as a string.
        javascript: JavaScript stored in ``metadata.script``.
        markdown_path: Read the markdown body from this file instead.
        language: ISO 639-1 language code.
        entity_view: Whether the page is an entity view template.

    Returns:
        ``{shared_id, title, url}`` for the created page.
    """
    if markdown_path is not None:
        markdown = Path(markdown_path).read_text(encoding="utf-8")
    if not markdown and not javascript:
        raise ValueError("Provide markdown (or markdown_path) and/or javascript.")

    metadata: dict[str, str] = {"content": markdown or ""}
    if javascript:
        metadata["script"] = javascript

    payload = {
        "title": title,
        "language": language,
        "entityView": entity_view,
        "metadata": metadata,
    }
    http = client().thesauris.http
    response = http.request_adapter.post(
        url=f"{http.url}/api/pages",
        headers=http.headers,
        cookies={"locale": language},
        data=json.dumps(payload),
    )
    response.raise_for_status()
    page = json.loads(response.content.decode("utf-8"))
    return {"shared_id": page.get("sharedId"), "title": page.get("title"), "url": page_url(page)}


def delete_pages_by_title(title: str, language: str = "en") -> dict[str, Any]:
    """Delete every page whose title matches ``title`` exactly.

    Returns:
        ``{deleted_count, shared_ids}`` for the pages that were removed.
    """
    http = client().thesauris.http
    targets = [p for p in fetch_pages(language) if p.get("title") == title]
    deleted: list[str] = []
    for page in targets:
        shared_id = page.get("sharedId")
        if not shared_id:
            continue
        response = http.request_adapter.delete(
            url=f"{http.url}/api/pages",
            headers=http.headers,
            cookies={"locale": language},
            params={"sharedId": shared_id},
        )
        response.raise_for_status()
        deleted.append(shared_id)
    return {"deleted_count": len(deleted), "shared_ids": deleted}


__all__ = [
    "client",
    "list_templates_summary",
    "fetch_entities_dataframe",
    "run_python_on_entities",
    "create_entity",
    "delete_entities",
    "list_thesauri",
    "add_thesauri_values",
    "fetch_pages",
    "list_pages",
    "page_url",
    "create_page",
    "delete_pages_by_title",
]
