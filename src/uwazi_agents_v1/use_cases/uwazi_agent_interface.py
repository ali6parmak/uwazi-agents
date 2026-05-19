from smolagents import tool
from uwazi_api.UwaziAdapter import UwaziAdapter

from uwazi_agents.config import url, user, password


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

        requested_fields = (
            [f.strip() for f in fields.split(",")] if fields != "all" else ["id", "name", "properties", "commonProperties"]
        )

        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<templates>"]

        for template in templates_raw:
            xml_parts.append("  <template>")

            if "id" in requested_fields:
                xml_parts.append(f'    <id>{template.get("_id", "")}</id>')

            if "name" in requested_fields:
                xml_parts.append(f'    <name>{template.get("name", "")}</name>')

            if "properties" in requested_fields:
                xml_parts.append("    <properties>")
                for prop in template.get("properties", []):
                    xml_parts.append("      <property>")
                    xml_parts.append(f'        <name>{prop.get("name", "")}</name>')
                    xml_parts.append(f'        <type>{prop.get("type", "")}</type>')
                    if prop.get("label"):
                        xml_parts.append(f'        <label>{prop.get("label", "")}</label>')
                    xml_parts.append("      </property>")
                xml_parts.append("    </properties>")

            if "commonProperties" in requested_fields:
                xml_parts.append("    <commonProperties>")
                for prop in template.get("commonProperties", []):
                    xml_parts.append("      <property>")
                    xml_parts.append(f'        <name>{prop.get("name", "")}</name>')
                    xml_parts.append(f'        <type>{prop.get("type", "")}</type>')
                    if prop.get("label"):
                        xml_parts.append(f'        <label>{prop.get("label", "")}</label>')
                    xml_parts.append("      </property>")
                xml_parts.append("    </commonProperties>")

            xml_parts.append("  </template>")

        xml_parts.append("</templates>")
        return "\n".join(xml_parts)
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
            batch = uwazi.entities.get(
                start_from=start_from, batch_size=batch_size, template_id=template_id, language=language
            )
            if not batch:
                break
            entities.extend(batch)
            if len(batch) < batch_size:
                break
            start_from += batch_size

        requested_fields = (
            [f.strip() for f in fields.split(",")]
            if fields != "all"
            else ["id", "sharedId", "title", "template", "metadata"]
        )

        xml_parts = ['<?xml version="1.0" encoding="UTF-8"?>', "<entities>"]

        for entity in entities:
            xml_parts.append("  <entity>")

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
                    xml_parts.append("    <metadata>")
                    for key, value in metadata.items():
                        xml_parts.append(f"      <{key}>{value}</{key}>")
                    xml_parts.append("    </metadata>")

            xml_parts.append("  </entity>")

        xml_parts.append("</entities>")
        return "\n".join(xml_parts)
    except Exception as e:
        return '<?xml version="1.0" encoding="UTF-8"?><entities></entities>'


@tool
def create_template(name: str, properties: list[dict], color: str = "#000000", language: str = "en") -> dict:
    """
    Creates a new template in the Uwazi instance.

    This tool creates a new template that defines the structure for entities in Uwazi.
    Templates contain properties that define what fields entities will have.

    AI agents should call this function with a template name and a list of property dictionaries.
    Each property is a simple dictionary with keys like label, type, required, etc.

    Args:
        name (str): The name of the template to create
        properties (list[dict]): List of property dictionaries. Each property dict can have:
            - label (str, required): Display name for the property. Avoid labels like "Title", "Date added", "Date modified" as they are already created by default
            - type (str, required): Property type - one of: text, markdown, numeric, date,
                                   link, select, multiselect, relationship, nested, image,
                                   media, preview, geolocation
            - required (bool, optional): If True, field is mandatory. Default: False
            - showInCard (bool, optional): Show in entity card preview. Default: False
            - filter (bool, optional): Can be used to filter entities. Default: False
            - defaultfilter (bool, optional): Show as default filter in UI. Default: False
            - prioritySorting (bool, optional): Prioritize in sorting. Default: False
            - noLabel (bool, optional): Hide label in UI. Default: False
            - style (str, optional): CSS style string. Default: ""
        color (str, optional): Hex color code for the template. Default: "#000000"
        language (str, optional): Language code for the template. Default: "en"

    Returns:
        dict: The created template with its generated ID, or error dict if creation fails

    Example usage for AI agents:
        create_template(
            name="Person",
            properties=[
                {"label": "Full Name", "type": "text", "required": True, "showInCard": True},
                {"label": "Biography", "type": "markdown"},
                {"label": "Birth Date", "type": "date", "filter": True}
            ],
            color="#4A90E2"
        )
    """
    try:
        if not all([url, user, password]):
            return {"error": "Missing required environment variables (UWAZI_URL, UWAZI_USER, UWAZI_PASSWORD)"}

        uwazi = UwaziAdapter(user=user, password=password, url=url)

        valid_property_fields = {
            "label",
            "type",
            "name",
            "required",
            "showInCard",
            "filter",
            "defaultfilter",
            "prioritySorting",
            "noLabel",
            "style",
            "generatedId",
            "isCommonProperty",
        }

        valid_property_types = {
            "text",
            "markdown",
            "numeric",
            "date",
            "link",
            "select",
            "multiselect",
            "relationship",
            "nested",
            "image",
            "media",
            "preview",
            "geolocation",
        }

        cleaned_properties = []
        for prop in properties:
            if not isinstance(prop, dict):
                continue

            if "type" not in prop:
                continue

            if prop["type"] not in valid_property_types:
                continue

            cleaned_prop = {key: value for key, value in prop.items() if key in valid_property_fields}

            if "label" not in cleaned_prop:
                cleaned_prop["label"] = ""

            cleaned_properties.append(cleaned_prop)

        template_dict = {
            "name": name,
            "color": color,
            "entityViewPage": "",
            "properties": cleaned_properties,
            "commonProperties": [
                {"label": "Title", "name": "title", "type": "text", "isCommonProperty": True},
                {"label": "Date added", "name": "creationDate", "type": "date", "isCommonProperty": True},
                {"label": "Date modified", "name": "editDate", "type": "date", "isCommonProperty": True},
            ],
        }

        result = uwazi.templates.set(language=language, template=template_dict)
        return result
    except Exception as e:
        return {"error": f"Error creating template: {str(e)}"}


if __name__ == "__main__":
    result = create_template(
        name="test_validation",
        properties=[
            {"label": "Valid Property", "type": "text", "required": True},
            {"label": "Invalid Type", "type": "invalid_type", "required": True},
            {"label": "Extra Fields", "type": "date", "invalid_field": "should be removed", "another_bad_field": 123},
            "not a dict",
            {"label": "Missing Type"},
            {"label": "Valid Markdown", "type": "markdown", "showInCard": True},
        ],
        color="#C03B22",
    )
    print(result)
