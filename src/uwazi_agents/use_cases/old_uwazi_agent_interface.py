import pandas as pd
from pandas import DataFrame
from smolagents import tool
from uwazi_api.UwaziAdapter import UwaziAdapter

from uwazi_agents.config import url, user, password


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
    print(template_name_to_template_id("foo"))
