import json
from collections import Counter
from typing import Any

from uwazi_api.client import UwaziClient
from uwazi_api.domain.entity import Entity
from uwazi_api.domain.thesauri import Thesauri

from configuration import UWAZI_PASSWORD, UWAZI_URL, UWAZI_USER 


def _fetch_thesauri_rows(client: UwaziClient, language: str = "en") -> list[dict[str, Any]]:
    http = client.thesauris.http
    response = http.request_adapter.get(
        url=f"{http.url}/api/thesauris",
        headers=http.headers,
        cookies={"locale": language},
    )
    return json.loads(response.content.decode("utf-8")).get("rows", [])


def _real_thesauri(rows: list[dict[str, Any]]) -> list[Thesauri]:
    return [Thesauri.model_validate(row) for row in rows if row.get("type") != "template"]


def check_uwazi():
    client = UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)
    template = client.templates.get_by_name("FooEntity")
    entities = client.entities.get(template_name="FooEntity", language="en", batch_size=10000)
    print(len(entities))
    print(entities[0])

def check_title_letters():
    client = UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)
    template_names: list[str] = [t.name for t in client.templates.get()]
    entities: list[Entity] = []
    for template in template_names:
        entities.extend(client.entities.get(template_name=template, language="en", batch_size=10000))
    print(f"Total number of entities: {len(entities)}")

    first_letter_counts = Counter([e.title[0].lower() for e in entities])
    print(first_letter_counts.most_common(5))

def create_entity(title: str, template_name: str, language: str = "en"):
    client = UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)
    template = client.templates.get_by_name(template_name)
    entity = client.entities.upload(entity=Entity(title=title, template=template.id, language=language), language=language)
    print(entity)

def check_thesauris():
    client = UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)
    rows = _fetch_thesauri_rows(client, language="en")
    thesauris = _real_thesauri(rows)

    template_rows = [r for r in rows if r.get("type") == "template"]
    if template_rows:
        print(
            "Note: /api/thesauris also returns template pick-lists for relationship fields "
            f"({len(template_rows)} skipped: {', '.join(r['name'] for r in template_rows)}).\n"
        )

    print(f"Thesauris ({len(thesauris)} total, same as Settings → Thesauris):\n")
    for thesauri in thesauris:
        print(f"  {thesauri.name}  (id={thesauri.id}, {len(thesauri.values)} label(s))")
        for value in thesauri.values:
            print(f"    - {value.label}")
        print()

    print("Templates using a thesaurus (select/multiselect → content id):")
    thesauri_by_id = {t.id: t.name for t in thesauris}
    for template in client.templates.get():
        for prop in template.properties + template.common_properties:
            if not prop.content:
                continue
            linked = thesauri_by_id.get(prop.content, prop.content)
            print(f"  {template.name}.{prop.name} → {linked}")

if __name__ == "__main__":
    # check_uwazi()
    # check_title_letters()
    # create_entity(title="Test", template_name="BarEntity", language="en")
    check_thesauris()
