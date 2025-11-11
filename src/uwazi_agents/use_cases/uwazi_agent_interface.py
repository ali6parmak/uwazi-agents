from smolagents import tool
from uwazi_api.UwaziAdapter import UwaziAdapter

from uwazi_agents.config import url, user, password
from uwazi_agents.domain.Template import Template
from uwazi_agents.domain.TemplateProperty import TemplateProperty


@tool
def get_all_templates(fields: str) -> str:
    """
    Retrieves all templates from Uwazi instance as XML with configurable field selection.

    This tool connects to a Uwazi instance and fetches all available templates.
    Templates define the structure of entities in Uwazi, containing properties
    that define the fields entities can have.

    AI agents can specify which fields to include in the XML output to reduce
    data size and processing time. Only the requested fields will be included
    in the response.

    Args:
        fields (str): Comma-separated list of fields to include in the XML output.
                      Available fields: id, name, properties, commonProperties
                      Example: "id,name,properties" to include template properties
                      Use "all" to include all available fields

    Returns:
        str: XML formatted string containing templates with requested fields.
             Returns empty templates element on error or if no credentials.
    """
    try:
        if not all([url, user, password]):
            return '<?xml version="1.0" encoding="UTF-8"?><templates></templates>'

        uwazi = UwaziAdapter(user=user, password=password, url=url)
        templates_raw = uwazi.templates.get()

        requested_fields = [f.strip() for f in fields.split(",")] if fields != "all" else ["id", "name", "properties", "commonProperties"]

        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<templates>']

        for template in templates_raw:
            xml_parts.append('  <template>')

            if "id" in requested_fields:
                xml_parts.append(f'    <id>{template.get("_id", "")}</id>')

            if "name" in requested_fields:
                xml_parts.append(f'    <name>{template.get("name", "")}</name>')

            if "properties" in requested_fields:
                xml_parts.append('    <properties>')
                for prop in template.get('properties', []):
                    xml_parts.append('      <property>')
                    xml_parts.append(f'        <name>{prop.get("name", "")}</name>')
                    xml_parts.append(f'        <type>{prop.get("type", "")}</type>')
                    if prop.get('label'):
                        xml_parts.append(f'        <label>{prop.get("label", "")}</label>')
                    xml_parts.append('      </property>')
                xml_parts.append('    </properties>')

            if "commonProperties" in requested_fields:
                xml_parts.append('    <commonProperties>')
                for prop in template.get('commonProperties', []):
                    xml_parts.append('      <property>')
                    xml_parts.append(f'        <name>{prop.get("name", "")}</name>')
                    xml_parts.append(f'        <type>{prop.get("type", "")}</type>')
                    if prop.get('label'):
                        xml_parts.append(f'        <label>{prop.get("label", "")}</label>')
                    xml_parts.append('      </property>')
                xml_parts.append('    </commonProperties>')

            xml_parts.append('  </template>')

        xml_parts.append('</templates>')
        return '\n'.join(xml_parts)
    except Exception as e:
        return '<?xml version="1.0" encoding="UTF-8"?><templates></templates>'


@tool
def get_all_entities(template_id: str, fields: str, batch_size: int = 30, language: str = "en") -> str:
    """
    Retrieves all entities for a given template from Uwazi instance as XML with configurable field selection.

    This tool connects to a Uwazi instance and fetches all entities for a specified template.
    It handles pagination automatically, retrieving entities in batches until all entities
    are collected.

    AI agents can specify which fields to include in the XML output to reduce
    data size and processing time. Only the requested fields will be included
    in the response.

    Args:
        template_id (str): The id of the template for which to retrieve entities.
        fields (str): Comma-separated list of fields to include in the XML output.
                      Available fields: id, sharedId, title, template, metadata
                      Example: "id,title" for minimal output
                      Use "all" to include all available fields
        batch_size (int): The number of entities to retrieve per batch (default: 30).
        language (str): The language in which to retrieve the entities (default: "en").

    Returns:
        str: XML formatted string containing entities with requested fields.
             Returns empty entities element on error or if no credentials.
    """
    try:
        if not all([url, user, password]):
            return '<?xml version="1.0" encoding="UTF-8"?><entities></entities>'

        uwazi = UwaziAdapter(user=user, password=password, url=url)
        entities = []
        start_from = 0
        while True:
            batch = uwazi.entities.get(start_from=start_from, batch_size=batch_size, template_id=template_id, language=language)
            if not batch:
                break
            entities.extend(batch)
            if len(batch) < batch_size:
                break
            start_from += batch_size

        requested_fields = [f.strip() for f in fields.split(",")] if fields != "all" else ["id", "sharedId", "title", "template", "metadata"]

        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<entities>']

        for entity in entities:
            xml_parts.append('  <entity>')

            if "id" in requested_fields and "_id" in entity:
                xml_parts.append(f'    <id>{entity.get("_id", "")}</id>')

            if "sharedId" in requested_fields and "sharedId" in entity:
                xml_parts.append(f'    <sharedId>{entity.get("sharedId", "")}</sharedId>')

            if "title" in requested_fields and "title" in entity:
                xml_parts.append(f'    <title>{entity.get("title", "")}</title>')

            if "template" in requested_fields and "template" in entity:
                xml_parts.append(f'    <template>{entity.get("template", "")}</template>')

            if "metadata" in requested_fields and "metadata" in entity:
                metadata = entity.get("metadata", {})
                if metadata:
                    xml_parts.append('    <metadata>')
                    for key, value in metadata.items():
                        xml_parts.append(f'      <{key}>{value}</{key}>')
                    xml_parts.append('    </metadata>')

            xml_parts.append('  </entity>')

        xml_parts.append('</entities>')
        return '\n'.join(xml_parts)
    except Exception as e:
        return '<?xml version="1.0" encoding="UTF-8"?><entities></entities>'


@tool
def create_template(template: Template, language: str = "en") -> dict:
    """
    Creates a new template in the Uwazi instance.

    This tool creates a new template that defines the structure for entities in Uwazi.
    Templates contain properties that define what fields entities of this type will have.

    How to use this tool:
    1. Create a Template object with name, optional color, and a list of TemplateProperty objects
    2. Each TemplateProperty should have a label (what users see), type (e.g., 'text', 'date'),
       and optional configuration (required, showInCard, filter, etc.)
    3. Pass the Template object to this function

    Example workflow for an AI agent:
    - To create a "Person" template with text fields for name and bio, and a date field for birth_date:
      1. Create TemplateProperty objects:
         - name_prop = TemplateProperty(label="Full Name", type="text", required=True, showInCard=True)
         - bio_prop = TemplateProperty(label="Biography", type="markdown", showInCard=False)
         - birth_prop = TemplateProperty(label="Birth Date", type="date", filter=True)
      2. Create Template object:
         - template = Template(name="Person", color="#4A90E2", properties=[name_prop, bio_prop, birth_prop])
      3. Call this function:
         - result = create_template(template=template, language="en")

    Available property types:
    - text: Single line text input
    - markdown: Multi-line text with markdown formatting
    - numeric: Numeric values
    - date: Date picker
    - link: URL links
    - select: Dropdown selection (single choice)
    - multiselect: Dropdown selection (multiple choices)
    - relationship: Link to other entities
    - nested: Nested sub-properties
    - image: Image upload
    - media: Media file upload
    - preview: Preview of linked documents
    - geolocation: Geographic coordinates

    Property configuration options (all optional, default to False/""):
    - required: If True, this field must be filled when creating entities
    - showInCard: If True, displays in entity card preview
    - filter: If True, can be used to filter entities in searches
    - defaultfilter: If True, shown as default filter in UI
    - prioritySorting: If True, prioritized in sorting operations
    - noLabel: If True, hides the label in the UI
    - style: CSS style string for custom styling

    Args:
        template (Template): A Template object containing name, optional color, and list of properties
        language (str): The language code for the template (default: "en")

    Returns:
        dict: The created template object with its generated ID, or error message if creation fails
    """
    try:
        if not all([url, user, password]):
            return {"error": "Missing required environment variables (UWAZI_URL, UWAZI_USER, UWAZI_PASSWORD)"}

        uwazi = UwaziAdapter(user=user, password=password, url=url)

        template_dict = template.model_dump(exclude_none=True, exclude={"id"})

        if "commonProperties" not in template_dict or template_dict["commonProperties"] is None:
            template_dict["commonProperties"] = [
                {"label": "Title", "name": "title", "type": "text", "isCommonProperty": True},
                {"label": "Date added", "name": "creationDate", "type": "date", "isCommonProperty": True},
                {"label": "Date modified", "name": "editDate", "type": "date", "isCommonProperty": True}
            ]

        result = uwazi.templates.set(language=language, template=template_dict)
        return result
    except Exception as e:
        return {"error": f"Error creating template: {str(e)}"}



if __name__ == '__main__':
    # pass
    # print(get_all_templates())
    # result = get_all_entities(template_id="6912059adeb0c2aa4cfc8ec4", fields="id")
    title_common_prop = TemplateProperty(
        label="Title",
        name="title",
        type="text",
        isCommonProperty=True
    )
    creation_date_common_prop = TemplateProperty(
        label="Date added",
        name="creationDate",
        type="date",
        isCommonProperty=True
    )
    edit_date_common_prop = TemplateProperty(
        label="Date modified",
        name="editDate",
        type="date",
        isCommonProperty=True
    )

    test_template = Template(
        name="test_2",
        color="#C03B22",
        properties=[],
        commonProperties=[
            title_common_prop,
            creation_date_common_prop,
            edit_date_common_prop
        ]
    )

    creation_result = create_template(template=test_template, language="en")
    print(creation_result)