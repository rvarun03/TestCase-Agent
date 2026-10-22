from langchain_core.tools import tool

from ..agents.requirement_agent import analyze_requirements

@tool
async def analyze_requirements_tool(brd_text: str) -> dict:
    """Analyze a BRD and extract testable requirements,
    business rules, and missing details.
    Use this before designing test scenarios.
    """

    analysis = await analyze_requirements(brd_text)

    return analysis.model_dump()