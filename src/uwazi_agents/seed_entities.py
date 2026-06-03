"""Bulk-create dummy entities so the agent has something big to chew on.

Edit the literal kwargs in the ``__main__`` block at the bottom of the
file to change what gets seeded, then run:

    python -m uwazi_agents.seed_entities

Uploads are intentionally serial: a single Uwazi instance handles them
best one at a time, and progress is printed so a multi-thousand run is
easy to monitor.
"""

from __future__ import annotations

import random
import string
import time

from uwazi_api.client import UwaziClient
from uwazi_api.domain.entity import Entity

from configuration import UWAZI_PASSWORD, UWAZI_URL, UWAZI_USER

_TITLE_LETTERS = string.ascii_uppercase


def _client() -> UwaziClient:
    return UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)


def _generate_title(prefix: str, index: int, vary_first_letter: bool, rng: random.Random) -> str:
    """Build a title.

    With ``vary_first_letter`` on, the first letter is randomly picked
    from A-Z so questions like "titles starting with C" actually have
    interesting answers across a big seed run.
    """
    if not vary_first_letter:
        return f"{prefix} {index}"
    letter = rng.choice(_TITLE_LETTERS)
    return f"{letter}{prefix} {index}"


def seed(
    template_name: str,
    count: int = 100,
    language: str = "en",
    title_prefix: str = "Test",
    start: int = 1,
    vary_first_letter: bool = False,
    seed_value: int | None = None,
) -> None:
    client = _client()
    template = client.templates.get_by_name(template_name)
    if template is None:
        raise SystemExit(
            f"Template {template_name!r} not found on {UWAZI_URL}. "
            "Create it in Uwazi first, or point template_name at an existing one."
        )
    template_id = template.id
    rng = random.Random(seed_value)

    print(
        f"Seeding {count} entities into template {template_name!r} "
        f"(id={template_id}, language={language}) starting at index {start}...",
        flush=True,
    )
    start_time = time.time()
    failures = 0
    for offset in range(count):
        index = start + offset
        title = _generate_title(title_prefix, index, vary_first_letter, rng)
        try:
            client.entities.upload(
                entity=Entity(title=title, template=template_id, language=language),
                language=language,
            )
        except Exception as exc:
            failures += 1
            print(f"  [{index}] upload failed: {type(exc).__name__}: {exc}", flush=True)
            continue
        done = offset + 1
        if done % 50 == 0 or done == count:
            elapsed = time.time() - start_time
            rate = done / elapsed if elapsed else 0.0
            remaining = (count - done) / rate if rate else 0.0
            print(
                f"  uploaded {done}/{count} " f"({rate:.1f}/s, ~{remaining:.0f}s remaining)",
                flush=True,
            )
    elapsed = time.time() - start_time
    print(f"Done. {count - failures}/{count} succeeded in {elapsed:.1f}s.", flush=True)


if __name__ == "__main__":
    seed(
        template_name="FooEntity",
        count=10000,
        vary_first_letter=True,
        seed_value=42,
    )
