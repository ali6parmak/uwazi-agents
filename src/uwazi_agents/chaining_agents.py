from smolagents import CodeAgent, tool
from smolagents.models import LiteLLMModel
import os
import json

# ============= SHARED TOOLS =============


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


# ============= SPECIALIZED TOOLS =============


@tool
def analyze_text_statistics(text: str) -> str:
    """
    Analyzes text and returns statistics like word count, character count, and more.

    Args:
        text: The text content to analyze

    Returns:
        JSON string containing text statistics including word count, character count, sentences, lines, and unique words
    """
    try:
        words = text.split()
        sentences = text.split(".")
        lines = text.split("\n")

        stats = {
            "total_characters": len(text),
            "total_words": len(words),
            "total_sentences": len([s for s in sentences if s.strip()]),
            "total_lines": len(lines),
            "average_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "unique_words": len(set(word.lower() for word in words)),
        }

        return json.dumps(stats, indent=2)
    except Exception as e:
        return f"Error analyzing text: {str(e)}"


@tool
def validate_content(content: str, min_words: int = 50) -> str:
    """
    Validates if content meets quality criteria such as minimum word count and paragraph structure.

    Args:
        content: The text content to validate
        min_words: Minimum number of words required (default: 50)

    Returns:
        Validation result message indicating pass or fail with specific issues
    """
    try:
        word_count = len(content.split())
        has_multiple_paragraphs = content.count("\n\n") >= 1

        issues = []
        if word_count < min_words:
            issues.append(f"Content too short: {word_count} words (minimum: {min_words})")
        if not has_multiple_paragraphs:
            issues.append("Content should have multiple paragraphs")

        if issues:
            return "VALIDATION FAILED:\n" + "\n".join(f"- {issue}" for issue in issues)
        else:
            return f"VALIDATION PASSED: Content meets all criteria ({word_count} words)"
    except Exception as e:
        return f"Error validating: {str(e)}"


@tool
def format_report(title: str, sections: str) -> str:
    """
    Formats data into a professional report structure with headers and sections.

    Args:
        title: The title of the report
        sections: The content sections to include in the report body

    Returns:
        Formatted report string with title, sections, and decorative borders
    """
    try:
        report = f"""
{'='*60}
{title.upper().center(60)}
{'='*60}

{sections}

{'='*60}
Report generated successfully
{'='*60}
"""
        return report
    except Exception as e:
        return f"Error formatting report: {str(e)}"


# ============= AGENT ORCHESTRATOR =============


class AgentPipeline:
    """Orchestrates multiple specialized agents working together."""

    def __init__(self, model):
        # Writer Agent - Creates content
        self.writer_agent = CodeAgent(
            tools=[create_text_file, read_text_file], model=model, additional_authorized_imports=["os"]
        )

        # Analyzer Agent - Analyzes content
        self.analyzer_agent = CodeAgent(
            tools=[read_text_file, analyze_text_statistics], model=model, additional_authorized_imports=["json"]
        )

        # Validator Agent - Checks quality
        self.validator_agent = CodeAgent(
            tools=[read_text_file, validate_content], model=model, additional_authorized_imports=[]
        )

        # Reporter Agent - Creates final reports
        self.reporter_agent = CodeAgent(
            tools=[read_text_file, format_report, create_text_file], model=model, additional_authorized_imports=[]
        )

    def run_pipeline(self, topic: str, output_file: str = "final_report.txt"):
        """Runs the complete agent pipeline."""

        print("\n" + "=" * 60)
        print("STARTING AGENT PIPELINE")
        print("=" * 60 + "\n")

        # Step 1: Writer Agent creates content
        print("📝 STEP 1: Writer Agent - Creating content...")
        print("-" * 60)
        writer_result = self.writer_agent.run(
            f"Create a file called 'draft.txt' with a detailed article about {topic}. "
            f"The article should be at least 100 words and have multiple paragraphs."
        )
        print(f"Writer Result: {writer_result}\n")

        # Step 2: Analyzer Agent analyzes the content
        print("📊 STEP 2: Analyzer Agent - Analyzing content...")
        print("-" * 60)
        analyzer_result = self.analyzer_agent.run("Read 'draft.txt' and analyze its text statistics. Return the statistics.")
        print(f"Analysis Result:\n{analyzer_result}\n")

        # Step 3: Validator Agent checks quality
        print("✅ STEP 3: Validator Agent - Validating quality...")
        print("-" * 60)
        validator_result = self.validator_agent.run(
            "Read 'draft.txt' and validate if the content meets quality criteria (minimum 50 words, multiple paragraphs)."
        )
        print(f"Validation Result: {validator_result}\n")

        # Step 4: Reporter Agent creates final report
        print("📋 STEP 4: Reporter Agent - Creating final report...")
        print("-" * 60)
        reporter_result = self.reporter_agent.run(
            f"Read 'draft.txt', then create a formatted report with title '{topic.upper()} - ANALYSIS REPORT' "
            f"that includes the original content and save it to '{output_file}'. "
            f"Add a section with these statistics: {analyzer_result}"
        )
        print(f"Reporter Result: {reporter_result}\n")

        print("=" * 60)
        print("✨ PIPELINE COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")

        return {
            "writer": writer_result,
            "analyzer": analyzer_result,
            "validator": validator_result,
            "reporter": reporter_result,
        }


# ============= MAIN EXECUTION =============


def main():
    # Initialize the model
    model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b", api_base="http://localhost:11434")

    # Create the pipeline
    pipeline = AgentPipeline(model)

    # Run the pipeline
    results = pipeline.run_pipeline(topic="Artificial Intelligence and Machine Learning", output_file="ai_ml_report.txt")

    # Display final results
    print("\n📁 FINAL OUTPUT:")
    print("-" * 60)
    if os.path.exists("ai_ml_report.txt"):
        with open("ai_ml_report.txt", "r") as f:
            print(f.read())

    print("*" * 100)
    print("*" * 100)

    print("RESULTS:")
    print(results)

    # Cleanup
    # print("\n🧹 Cleaning up temporary files...")
    # for file in ["draft.txt"]:
    #     if os.path.exists(file):
    #         os.remove(file)
    #         print(f"Removed {file}")


if __name__ == "__main__":
    main()
