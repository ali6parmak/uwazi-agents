from uwazi_api.client import UwaziClient
from uwazi_api.domain.entity import Entity
from collections import Counter
from configuration import UWAZI_PASSWORD, UWAZI_URL, UWAZI_USER


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



if __name__ == "__main__":
    # check_uwazi()
    check_title_letters()
