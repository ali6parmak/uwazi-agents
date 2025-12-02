import pandas as pd
from pandas import DataFrame
from smolagents import tool
from uwazi_api.UwaziAdapter import UwaziAdapter

from uwazi_agents.config import url, user, password


@tool
def template_name_to_template_id(template_name: str) -> str:
    """
    Converts a template name to its corresponding template ID in the Uwazi instance.

    This tool connects to a Uwazi instance and retrieves all templates,
    searching for the one that matches the provided template name.
    If found, it returns the template's unique ID.

    Args:
        template_name (str): The name of the template to look up.
    Returns:
        str: The template ID if found, otherwise an empty string.
    """
    try:
        if not all([url, user, password]):
            return ""

        uwazi = UwaziAdapter(user=user, password=password, url=url)
        templates = uwazi.templates.get()

        for template in templates:
            if template.get("name", "").lower() == template_name.lower():
                return template.get("_id", "")

        return ""
    except Exception as e:
        return ""


@tool
def get_entities_from_template(template_name: str) -> tuple[DataFrame | None, list[str], list[str]]:
    """
    Retrieves all entities from Uwazi instance for a given template name as a DataFrame and returns the DataFrame, its column names, and column types.

    Args:
        template_name (str): The name of the template for which to retrieve entities.

    Returns:
        tuple[DataFrame | None, list[str], list[str]]: Tuple containing the DataFrame with entities data (or None on error or missing credentials), a list of column names, and a list of column types. Some of the properties are preceded by "metadata_" as they are custom properties from the template.
    """
    try:

        if not all([url, user, password]):
            return None, [], []

        uwazi_adapter = UwaziAdapter(user=user, password=password, url=url)

        start = 0
        batch_size = 100
        dataframes = []
        while True:
            batch = uwazi_adapter.entities.get_pandas_dataframe(
                start_from=start,
                batch_size=start + batch_size,
                template_id=template_name_to_template_id(template_name),
                language="en",
                published=False,
            )

            if batch is None or (isinstance(batch, pd.DataFrame) and batch.empty):
                break

            dataframes.append(batch)
            start += batch_size

        if dataframes:
            combined_df = pd.concat(dataframes, ignore_index=True)
            col_names = list(combined_df.columns)
            col_types = [str(combined_df[col].dtype) for col in col_names]
            return combined_df, col_names, col_types
        else:
            return None, [], []
    except Exception as e:
        return None, [], []


if __name__ == "__main__":
    print(template_name_to_template_id("foo"))
