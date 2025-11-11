from smolagents import tool


@tool
def create_text_file(file_path: str, content: str) -> str:
    """
    Creates a text file at the given path with the specified content.

    Args:
        file_path: The path where the file should be created (e.g., 'output.txt')
        content: The text content to write to the file

    Returns:
        A success message or error description
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully created file at {file_path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"
