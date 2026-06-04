import json
from collections import Counter
from typing import Any

import pandas as pd
from uwazi_api.client import UwaziClient
from uwazi_api.domain.entity import Entity
from uwazi_api.domain.property_schema import PropertySchema
from uwazi_api.domain.template import PropertyType, Template
from uwazi_api.domain.thesauri import Thesauri

from configuration import UWAZI_PASSWORD, UWAZI_URL, UWAZI_USER


def _fetch_thesauri_rows(
    client: UwaziClient, language: str = "en"
) -> list[dict[str, Any]]:
    http = client.thesauris.http
    response = http.request_adapter.get(
        url=f"{http.url}/api/thesauris",
        headers=http.headers,
        cookies={"locale": language},
    )
    return json.loads(response.content.decode("utf-8")).get("rows", [])


def _real_thesauri(rows: list[dict[str, Any]]) -> list[Thesauri]:
    return [
        Thesauri.model_validate(row) for row in rows if row.get("type") != "template"
    ]


def check_uwazi():
    client = UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)
    template = client.templates.get_by_name("FooEntity")
    entities = client.entities.get(
        template_name="FooEntity", language="en", batch_size=10000
    )
    print(len(entities))
    print(entities[0])


def check_title_letters():
    client = UwaziClient(user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL)
    template_names: list[str] = [t.name for t in client.templates.get()]
    entities: list[Entity] = []
    for template in template_names:
        entities.extend(
            client.entities.get(template_name=template, language="en", batch_size=10000)
        )
    print(f"Total number of entities: {len(entities)}")

    first_letter_counts = Counter([e.title[0].lower() for e in entities if e.title])
    print(first_letter_counts.most_common(5))


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
            print(f"    - {value.label} - {value.id}")
        print()

    print("Templates using a thesaurus (select/multiselect → content id):")
    thesauri_by_id = {t.id: t.name for t in thesauris}
    for template in client.templates.get():
        for prop in template.properties + template.common_properties:
            if not prop.content:
                continue
            linked = thesauri_by_id.get(prop.content, prop.content)
            print(f"  {template.name}.{prop.name} → {linked}")


def add_thesauris(template_name: str, property_name: str, values: list[str]):
    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    df: pd.DataFrame = pd.DataFrame({property_name: values})
    client.thesauri_from_df.execute(df=df, template_name=template_name, language="en")


def create_entity(title: str, template_name: str, language: str = "en"):
    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    template: Template | None = client.templates.get_by_name(template_name)
    if not template:
        print(f"No template found named: {template_name}")
        return
    entity: Entity = Entity(title=title, template=template.id, language=language)
    entity_id: str = client.entities.upload(entity=entity, language=language)
    print(entity_id)


def delete_entities(template_name: None | str = None):
    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    entities = client.entities.get(
        start_from=0, batch_size=9999, template_name=template_name
    )
    shared_ids_to_delete: list[str] = []
    for e in entities:
        template_id: str | None = e.template
        if template_id is None:
            continue
        template: Template | None = client.templates.get_by_id(template_id)
        if template is None:
            continue
        print(f"{template_id=}, {template.name=}, {e.title=}")
        print(e)
        print("*" * 25)
        shared_id: str | None = e.shared_id
        if shared_id:
            shared_ids_to_delete.append(shared_id)
    print(len(shared_ids_to_delete))
    client.entities.delete_entities(shared_ids=shared_ids_to_delete)


def get_templates() -> None:
    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    templates: list[Template] = client.templates.get()
    for t in templates:
        print(f"{t.id}, {t.name}")

    template_fooentity_by_name: Template | None = client.templates.get_by_name(
        template_name="FooEntity"
    )
    template_fooentity_by_id: Template | None = client.templates.get_by_id(
        template_id="6a0d832f2572c9826000bba6"
    )

    if not template_fooentity_by_name or not template_fooentity_by_id:
        return

    print(
        f"Template foo entity by name: {template_fooentity_by_name.id} - {template_fooentity_by_name.name}"
    )
    print(
        f"Template foo entity by id: {template_fooentity_by_id.id} - {template_fooentity_by_id.name}"
    )

    template_barentity: Template | None = client.templates.get_by_name(
        template_name="BarEntity"
    )
    if not template_barentity:
        return

    barentity_properties: list[PropertySchema] = template_barentity.properties
    print(barentity_properties)

    print("*" * 10)
    barentity_name: str = template_barentity.name
    barentity_country_property: PropertySchema = client.templates.find_property(
        template_name_or_id=barentity_name, prop_name="Country"
    )
    print(barentity_country_property)


def create_template(template_name: str, language: str = "en") -> None:
    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    template: Template = Template(name=template_name)
    client.templates.set(language, template)


def delete_template(template_name: str, force_delete=False):
    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    template: Template | None = client.templates.get_by_name(template_name)
    if not template:
        print(f"Template {template_name} not found.")
        return
    template_id: str | None = template.id
    if not template_id:
        return

    if force_delete:
        delete_entities(template_name)

    client.templates.delete_empty_template(template_id)


def add_property_to_template(
    template_name: str, property_name: str, property_type: str, language: str = "en"
) -> None:

    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    template: Template | None = client.templates.get_by_name(template_name)
    if not template:
        print(f"No template named {template_name}")
        return
    print(template.properties)

    _property_type = property_type.lower()
    property: PropertySchema = PropertySchema(
        name=property_name, label=property_name, type=PropertyType(_property_type)
    )
    template.properties.append(property)
    client.templates.set(language, template)


def update_entity_property(
    template_name: str,
    property_name: str,
    property_value: str,
    entity_title: str | None = None,
) -> None:
    client: UwaziClient = UwaziClient(
        user=UWAZI_USER, password=UWAZI_PASSWORD, url=UWAZI_URL
    )
    template: Template | None = client.templates.get_by_name(template_name)
    if not template:
        print(f"No template named {template_name}")
        return

    entities: list[Entity] = client.entities.get(
        start_from=0, batch_size=9999, template_name=template.name
    )
    if entity_title:
        entities = [e for e in entities if e.title == entity_title]

    for entity in entities:
        entity.metadata[property_name.lower()] = property_value
        language: str | None = entity.language
        if not language:
            continue
        client.entities.update_partially(entity, language)

    print(entities[0])


if __name__ == "__main__":
    # check_uwazi()
    # check_title_letters()
    # create_entity(title="Test", template_name="BarEntity", language="en")
    # create_entity("Z Test", "TestEntityTemplate", "en")
    # delete_entities(template_name="BarEntity")
    check_thesauris()
    # add_thesauris(template_name="BarEntity", property_name="Country", values=["Malawi", "Zambia", "Mozambique"])
    # get_thesauris()
    # get_templates()
    # create_template("TestEntityTemplate")
    # delete_template("TestEntityTemplate")
    # add_property_to_template("TestEntityTemplate", "Media", "media")
    # update_entity_property("TestEntityTemplate", "Text", "This is an example text.")
