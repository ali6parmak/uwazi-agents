import os
from time import time

from smolagents import CodeAgent, ToolCallingAgent
from smolagents.models import LiteLLMModel

from uwazi_agents.use_cases.uwazi_agent_interface import get_all_templates, get_all_entities, create_template


def run_uwazi_agent(prompt):
    # model = LiteLLMModel(model_id="ollama/qwen2.5-coder:14b", api_base="http://localhost:11434", temperature=0.2)
    # model = LiteLLMModel(model_id="ollama/gemma3:12b", api_base="http://localhost:11434")
    # model = LiteLLMModel(model_id="gemini/gemini-2.5-flash", api_key=os.getenv("GOOGLE_API_KEY"))
    model = LiteLLMModel(model_id="gemini/gemini-2.5-pro", api_key=os.getenv("GOOGLE_API_KEY"))
    # agent = ToolCallingAgent(
    #     tools=[get_all_templates, get_all_entities, create_template],
    #     model=model
    # )
    agent = CodeAgent(
        tools=[create_template],
        model=model,
        additional_authorized_imports=["xml.*", "uwazi_agents.domain.Template", "uwazi_agents.domain.TemplateProperty"],
        use_structured_outputs_internally=True,
    )

    agent.run(prompt)


if __name__ == "__main__":
    start = time()
    # run_uwazi_agent("How many entities contains the template foo")
    run_uwazi_agent(
        "Create as many templates as necessary to divide the data in the different types for holding the data for the organization The Armed Conflict Location & Event Data Project"
    )
    print("time", round(time() - start, 2), "s")
