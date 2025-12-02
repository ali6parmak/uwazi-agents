import os
from smolagents import CodeAgent, GradioUI
from smolagents.models import LiteLLMModel

from uwazi_agents.use_cases.uwazi_agent_interface import get_entities_from_template


def run_uwazi_agent():
    # model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b", api_base="http://localhost:11434", temperature=0.2)
    model = LiteLLMModel(model_id="gemini/gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY"))
    # model = LiteLLMModel(model_id="gemini/gemini-2.5-pro", api_key=os.getenv("GOOGLE_API_KEY"))
    agent = CodeAgent(
        tools=[get_entities_from_template],
        additional_authorized_imports=["pandas.*"],
        model=model,
        use_structured_outputs_internally=False,
    )

    GradioUI(agent).launch()


if __name__ == "__main__":
    run_uwazi_agent()
