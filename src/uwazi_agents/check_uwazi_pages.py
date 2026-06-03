"""Scratch helpers for poking at Uwazi pages.

The reusable page primitives now live in ``uwazi_agents.uwazi_tools`` so the
agent and these checks share a single implementation. This module keeps only
the extras that aren't part of the agent's toolset: updating a page and
deleting one by its ``sharedId``.
"""

import json
from pathlib import Path
from typing import Any

from uwazi_agents.uwazi_tools import (
    client,
    create_page,
    delete_pages_by_title,
    fetch_pages,
    list_pages,
    page_url,
)


def update_page(
    shared_id: str,
    *,
    title: str | None = None,
    markdown_path: str | Path | None = None,
    content: str | None = None,
    javascript: str | None = None,
    language: str = "en",
    entity_view: bool | None = None,
) -> dict[str, Any]:
    """Update an existing page (POST /api/pages with ``_id`` and ``sharedId``)."""
    existing = next((p for p in fetch_pages(language) if p["sharedId"] == shared_id), None)
    if existing is None:
        raise ValueError(f"No page with sharedId={shared_id!r}")

    if markdown_path is not None:
        content = Path(markdown_path).read_text(encoding="utf-8")

    metadata = dict(existing.get("metadata") or {})
    if content is not None:
        metadata["content"] = content
    if javascript is not None:
        metadata["script"] = javascript

    payload: dict[str, Any] = {
        "_id": existing["_id"],
        "sharedId": shared_id,
        "title": title if title is not None else existing["title"],
        "language": language,
        "entityView": entity_view if entity_view is not None else existing.get("entityView", False),
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
    print(f"Updated page: {page_url(page)}")
    return page


def delete_page(shared_id: str, language: str = "en") -> None:
    """Delete a single page by its ``sharedId``."""
    http = client().thesauris.http
    response = http.request_adapter.delete(
        url=f"{http.url}/api/pages",
        headers=http.headers,
        cookies={"locale": language},
        params={"sharedId": shared_id},
    )
    response.raise_for_status()
    print(f"Deleted page sharedId={shared_id}: {response.content.decode()}")


if __name__ == "__main__":
    # create_page("MyPage", markdown_path="README.md")
    # create_page("MyPage2", markdown="# Hello\n\nFrom a string.", javascript="console.log('hi')")
    # delete_pages_by_title("MyPage2")
    print(json.dumps(list_pages(), indent=2))
