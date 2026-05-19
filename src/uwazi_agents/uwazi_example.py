from datetime import date

import pandas as pd
from uwazi_api.client import UwaziClient
from uwazi_api.domain.search_filters import DateRange, SearchFilters

from configuration import UWAZI_PASSWORD, UWAZI_URL, UWAZI_USER

_OPEN_PAST = date(1900, 1, 1)
_OPEN_FUTURE = date(2100, 1, 1)


def _client() -> UwaziClient:
    return UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)


def search_with_filters(
    template_name: str | None = None,
    language: str = "en",
    date_from: date | None = None,
    date_to: date | None = None,
    batch_size: int = 100,
) -> pd.DataFrame:
    """Filter-based search returning a DataFrame.

    Mirrors the user's reference query exactly: build a ``SearchFilters``
    object (optionally with a ``date`` ``DateRange``) and forward the
    rest of the parameters to ``search_by_filter_to_dataframe``.
    """
    filters = SearchFilters()
    if date_from is not None or date_to is not None:
        filters.add(
            "date",
            DateRange(from_=date_from or _OPEN_PAST, to=date_to or _OPEN_FUTURE),
        )
    return _client().search.search_by_filter_to_dataframe(
        filters=filters,
        template_name=template_name,
        language=language,
        batch_size=batch_size,
    )


def search_by_text(
    search_term: str,
    template_name: str | None = None,
    language: str = "en",
    batch_size: int = 20,
) -> pd.DataFrame:
    """Free-text search over Uwazi entities, returned as a DataFrame.

    The underlying client returns ``Entity`` objects; we project the
    interesting columns so the result fits in an LLM context window.
    """
    entities = _client().search.search_by_text(
        search_term=search_term,
        template_name=template_name,
        language=language,
        batch_size=batch_size,
    )
    rows = [
        {
            "shared_id": e.shared_id,
            "title": e.title,
            "template": e.template,
            "language": e.language,
        }
        for e in entities
    ]
    return pd.DataFrame(rows)


def search() -> pd.DataFrame:
    """Reference query the agents are expected to reproduce from prose.

    "I want to see all the documents that have Resolution template in
    French from 10 January 2020 to 18 May 2026".
    """
    return search_with_filters(
        template_name="Resolution",
        language="fr",
        date_from=date(2020, 1, 10),
        date_to=date(2026, 5, 18),
        batch_size=100,
    )


if __name__ == "__main__":
    df = search_by_text("title:Plan", template_name=None, batch_size=100)
    print(df.to_string())
