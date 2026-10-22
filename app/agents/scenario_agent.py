from langchain.agents import create_agent

from ..llm import get_llm
from ..models import ScenarioResponse
from ..tools.agent_tools import analyze_requirements_tool

SYSTEM_PROMPT = """
You are a Test Scenario Design Agent.

Your task is to generate high-quality test scenarios
from a Business Requirements Document.

You have access to analyze_requirements_tool.

Use this tool to obtain structured requirements
before designing test scenarios.

Generate:
- Positive scenarios
- Negative scenarios
- Boundary scenarios
- Role-based scenarios

Rules:
- Every scenario must reference a requirement ID.
- Do not invent unsupported functionality.
- Do not invent validation limits or business rules.
- Generate clear, testable scenarios.
"""

def get_scenario_agent():

    return create_agent(
        model=get_llm(),
        tools=[analyze_requirements_tool]
    )

async def design_scenarios(brd_text: str) -> ScenarioResponse:

    agent = get_scenario_agent()

    result = await agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": brd_text
            }
        ]
    })

    for message in result["messages"]:

        if getattr(message, "tool_calls", None):
            print("AGENT 2 TOOL CALL:", message.tool_calls)

        if message.type == "tool":
            print("AGENT 1 RESULT:", message.content)

    print("RESULT KEYS:", result.keys())

    for message in result["messages"]:
        print("MESSAGE TYPE:", message.type)
        print("CONTENT:", message.content)

        if getattr(message, "tool_calls", None):
            print("TOOL CALLS:", message.tool_calls)

    print("STRUCTURED RESPONSE:", result.get("structured_response"))

    return result.get("structured_response")
