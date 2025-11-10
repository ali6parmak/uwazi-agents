from smolagents import CodeAgent, tool
from smolagents.models import LiteLLMModel
from typing import Optional
import os


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


@tool
def remove_text_file(file_path: str) -> str:
    """
    Removes a text file from the given path.

    Args:
        file_path: The path of the file to remove

    Returns:
        A success message or error description
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return f"Successfully removed file at {file_path}"
        else:
            return f"File not found at {file_path}"
    except Exception as e:
        return f"Error removing file: {str(e)}"


@tool
def update_text_file(file_path: str, new_content: str, mode: Optional[str] = "overwrite") -> str:
    """
    Updates an existing text file with new content.

    Args:
        file_path: The path of the file to update
        new_content: The new content to write
        mode: Either 'overwrite' to replace content or 'append' to add to existing content

    Returns:
        A success message or error description
    """
    try:
        if not os.path.exists(file_path):
            return f"File not found at {file_path}"

        write_mode = "w" if mode == "overwrite" else "a"
        with open(file_path, write_mode, encoding="utf-8") as f:
            f.write(new_content)

        action = "overwritten" if mode == "overwrite" else "appended to"
        return f"Successfully {action} file at {file_path}"
    except Exception as e:
        return f"Error updating file: {str(e)}"


@tool
def read_text_file(file_path: str) -> str:
    """
    Reads and returns the content of a text file.

    Args:
        file_path: The path of the file to read

    Returns:
        The file content or error description
    """
    try:
        if not os.path.exists(file_path):
            return f"File not found at {file_path}"

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


def main():

    model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b", api_base="http://localhost:11434", temperature=0.2)

    agent = CodeAgent(
        tools=[create_text_file, remove_text_file, update_text_file, read_text_file],
        model=model,
        additional_authorized_imports=["os"],
    )

    # i = input("Enter the task: ")
    # while i != "exit":
    #     result = agent.run(i)
    #     print(f"Result: {result}\n")
    #     i = input("Enter the task: ")

    print("=== Example 1: Create the file ===")
    result = agent.run("Create a text file called 'test.txt' with the content 'Hello, AI Agents!'")
    print(f"Result: {result}\n")

    print("=== Example 2: Read the file ===")
    result = agent.run("Read the content of 'test.txt'")
    print(f"Result: {result}\n")

    print("=== Example 3: Update the file ===")
    result = agent.run("Append the text '\\nThis is a new line.' to 'test.txt'")
    print(f"Result: {result}\n")

    print("=== Example 4: Read updated file ===")
    result = agent.run("Read the content of 'test.txt' again")
    print(f"Result: {result}\n")

    print("=== Example 5: Remove the file ===")
    result = agent.run("Remove the file 'test.txt'")
    print(f"Result: {result}\n")

    result = agent.run("Write Python code to calculate the factorial of 7 and print the result.")
    print(result)


if __name__ == "__main__":

    main()
