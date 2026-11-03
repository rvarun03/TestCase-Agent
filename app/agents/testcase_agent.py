from functools import lru_cache

from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call
from langchain_core.messages import ToolMessage

from ..llm import get_llm
from ..tools.qa_tools import BRDContext, generate_test_case_report


@wrap_model_call
async def require_report_tool(request, handler):
    """Make the agent take its one safe, relevant action on every BRD."""
    return await handler(request.override(tool_choice="generate_test_case_report"))


@lru_cache(maxsize=1)
def _get_agent():
    """Build a constrained, tool-calling agent once per process."""
    return create_agent(
        model=get_llm(),
        tools=[generate_test_case_report],
        middleware=[require_report_tool],
        context_schema=BRDContext,
        # The tool result is the report, so do not make a redundant final LLM call.
        interrupt_after=["tools"],
        name="brd_test_case_agent",
    )


def _report_tool_text(result: dict) -> str:
    """Extract the report produced by the agent's tool."""
    for message in reversed(result.get("messages", [])):
        if isinstance(message, ToolMessage) and message.name == "generate_test_case_report":
            if isinstance(message.content, str) and message.content.strip():
                return message.content.strip()

    raise RuntimeError("The agent completed without generating a test-case report.")


class TestCaseAgent:
    """A single-action LangChain agent for BRD QA test-case generation."""

    async def generate(
        self, 
        brd_text: str,
        additional_instructions: str = ""
        ) -> str:
        result = await _get_agent().ainvoke(
            {
                "messages": [
                    (
                        "user",
                        "Generate the BRD test-case report using the available tool.",
                    )
                ],
            },
            context={
                "brd_text": brd_text,
                "additional_instructions": additional_instructions},
        )
        return _report_tool_text(result)


async def generate_test_cases(
        brd_text: str,
        additional_instructions: str = ""
        ) -> str:
    """Public entry point used by the API route."""
    return await TestCaseAgent().generate(
        brd_text,
        additional_instructions=additional_instructions)
