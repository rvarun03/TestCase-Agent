from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from typing_extensions import TypedDict

from ..llm import get_llm


class BRDContext(TypedDict):
    """BRD data kept out of the model-visible tool schema."""

    brd_text: str


def _text_content(response: object) -> str:
    """Return an LLM response as text for passing between agent tools."""
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)


async def _generate_text(instructions: str, input_text: str) -> str:
    """Generate text and retry once when a provider returns an empty response."""
    for _ in range(2):
        response = await get_llm().ainvoke([
            ("system", instructions),
            ("human", input_text),
        ])
        content = _text_content(response).strip()
        if content:
            return content

    raise RuntimeError("The model returned an empty response. Please try again.")


@tool
async def gather_requirements(brd_text: str) -> str:
    """Extract a concise, numbered list of testable requirements from a BRD."""
    return await _generate_text(
        "Extract only the most important testable requirements from the BRD. Do "
        "not invent details. Return at most 10 concise numbered requirements, "
        "ordered by business priority. Return plain text; do not return JSON.",
        brd_text,
    )


@tool
async def generate_scenarios(requirements_text: str) -> str:
    """Turn a requirement list into positive, negative, boundary, and role-based test scenarios."""
    return await _generate_text(
        "Create concise test scenarios from the supplied requirements. Return at "
        "most two scenarios per requirement: one happy path and one negative or "
        "validation case only when that behavior is explicitly stated. Do not "
        "invent field lengths, roles, files, error messages, or rules. Keep the "
        "requirement number beside each scenario. Return plain text, not JSON.",
        requirements_text,
    )


@tool
async def create_test_cases(scenarios_text: str) -> str:
    """Turn test scenarios into concise manual test cases ready for a QA demo."""
    return await _generate_text(
        "Create at most 8 high-value, executable manual test cases from the "
        "supplied scenarios. Do not invent behavior; when a detail is absent, "
        "state 'Not specified in BRD' rather than making one up. Return Markdown "
        "only in exactly this plain-text structure:\n\n"
        "BRD TEST CASES\n"
        "COVERAGE: ...\n\n"
        "TEST CASE: TC-001\n"
        "Title: <title>\n"
        "Requirement: <source requirement>\n"
        "Type: Happy path | Validation\n"
        "Priority: High | Medium | Low\n"
        "Preconditions: ...\n"
        "Steps:\n1. ...\n2. ...\n"
        "Expected result: ...\n"
        "----------------------------------------\n\n"
        "BRD GAPS / ASSUMPTIONS\n"
        "- ...",
        scenarios_text,
    )


@tool
async def generate_test_case_report(runtime: ToolRuntime[BRDContext]) -> str:
    """Generate a QA report from the BRD securely supplied in runtime context."""
    brd_text = runtime.context["brd_text"]
    return await _generate_text(
        "Generate a concise, high-value manual QA test-case report from this BRD. "
        "Identify only explicit, testable requirements, then create at most 8 test "
        "cases covering happy paths and stated validation behavior. Do not invent "
        "behavior; when a detail is absent, state 'Not specified in BRD'. Return "
        "Markdown only in exactly this plain-text structure:\n\n"
        "BRD TEST CASES\n"
        "COVERAGE: ...\n\n"
        "TEST CASE: TC-001\n"
        "Title: <title>\n"
        "Requirement: <source requirement>\n"
        "Type: Happy path | Validation\n"
        "Priority: High | Medium | Low\n"
        "Preconditions: ...\n"
        "Steps:\n1. ...\n2. ...\n"
        "Expected result: ...\n"
        "----------------------------------------\n\n"
        "BRD GAPS / ASSUMPTIONS\n"
        "- ...",
        brd_text,
    )
