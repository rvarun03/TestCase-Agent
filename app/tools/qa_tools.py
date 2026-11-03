from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime
from typing_extensions import TypedDict

from ..llm import get_llm


class BRDContext(TypedDict):
    """BRD data kept out of the model-visible tool schema."""

    brd_text: str
    additional_instructions: str


def _text_content(response: object) -> str:
    """Return an LLM response as text for passing between agent tools."""
    content = getattr(response, "content", response)
    return content if isinstance(content, str) else str(content)


def _additional_instructions_block(additional_instructions: str) -> str:
    """Format request-specific generation instructions for an LLM prompt."""
    if not additional_instructions.strip():
        return "No additional instructions were provided."

    return (
        "Follow these request-specific instructions unless they conflict with "
        "the evidence-only and no-invention rules:\n"
        f"{additional_instructions.strip()}"
    )


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
async def gather_requirements(
    brd_text: str,
    additional_instructions: str = "",
) -> str:
    """Extract a concise, numbered list of testable requirements from a BRD."""
    return await _generate_text(
        f"""
        You are a senior QA requirements analyst.

        Analyze ONLY the current supplied document,
        screenshot observations and user description.

        Your goal is to identify meaningful testable
        application behavior, not simply list UI elements.

        STEP 1: IDENTIFY FUNCTIONAL REQUIREMENTS

        Identify user actions and application workflows
        supported by the available evidence.

        Examples of functional interactions:
        - Entering credentials
        - Submitting a login form
        - Activating password recovery
        - Creating, editing or deleting records
        - Searching or filtering data
        - Submitting forms

        These are examples, not requirements to invent.
        Include only interactions relevant to current inputs.

        A visible control supports proposing a test of
        its interaction, but does not prove its behavior.

        STEP 2: IDENTIFY UI REQUIREMENTS

        Identify important visible controls and states.

        Combine related UI checks into one requirement.
        Do not create separate requirements for every
        icon, logo, color, background or footer element.

        STEP 3: IDENTIFY NON-FUNCTIONAL REQUIREMENTS

        Include only expectations supported by
        explicit documentation or user instructions.

        RULES:
        - Prioritize core application functionality.
        - Do not invent application behavior.
        - Do not invent validation rules or error messages.
        - If behavior is not documented, mark it
          "Requires verification".
        - Never claim an interaction was successfully tested.
        - Do not use previous requests or conversations.

        OUTPUT ORDER:

        FUNCTIONAL REQUIREMENTS

        REQ-F001: ...
        Evidence: Documented | Visible UI | Requires verification

        UI REQUIREMENTS

        REQ-U001: ...
        Evidence: Visible UI | Documented

        NON-FUNCTIONAL REQUIREMENTS

        REQ-N001: ...
        Evidence: Documented

        Generate only requirements supported by
        the current input. Do not pad categories.
        REQUEST-SPECIFIC INSTRUCTIONS:
        {_additional_instructions_block(additional_instructions)}

        If the request-specific instructions say to generate only functional
        output, omit the UI REQUIREMENTS and NON-FUNCTIONAL REQUIREMENTS
        sections entirely. Otherwise, use the output order below.
        """,
        brd_text,
    )


@tool
async def generate_scenarios(
    requirements_text: str,
    additional_instructions: str = "",
) -> str:
    """Turn a requirement list into positive, negative, boundary, and role-based test scenarios."""
    return await _generate_text(
        f"""
        You are a senior QA test scenario engineer.

        Generate test scenarios from the supplied
        requirements.

        CRITICAL:
        Prioritize application functionality over
        visual appearance.

        GENERATE IN THIS ORDER:

        SECTION 1: FUNCTIONAL SCENARIOS

        For every supported functional requirement,
        identify meaningful user interactions.

        Cover where relevant:
        - Valid user actions
        - Invalid inputs
        - Form submissions
        - Navigation actions
        - Documented validation behavior
        - Documented business rules

        If an action is visible but the outcome is unknown,
        create a proposed test scenario and mark the
        expected result as "Requires verification".

        Do not invent specific validation messages.

        SECTION 2: UI SCENARIOS

        Generate scenarios for significant UI elements.

        Group related visual checks.
        Avoid individual scenarios for each logo,
        icon, color or decorative component.

        SECTION 3: NON-FUNCTIONAL SCENARIOS

        Only generate when supported by documented
        requirements.

        IMPORTANT:
        - Generate functional scenarios first.
        - Do not drop supported functional workflows.
        - Avoid duplicate scenarios.
        - Every scenario must reference a requirement ID.
        - Use only the provided input.
        - Do not claim undocumented behavior is confirmed.

        FORMAT:

        FUNCTIONAL SCENARIOS

        Scenario ID: SC-F001
        Requirement ID: ...
        Title: ...
        Test Type: Functional
        Test Intent: Positive | Negative
        Description: ...
        Expected Behavior: ...
        Evidence: Documented | Requires verification

        ----------------------------------------

        UI SCENARIOS

        Scenario ID: SC-U001
        Requirement ID: ...
        Title: ...
        Test Type: UI
        Test Intent: Positive | Negative
        Description: ...
        Expected Behavior: ...
        Evidence: Documented | Visible UI

        ----------------------------------------

        NON-FUNCTIONAL SCENARIOS

        Scenario ID: SC-N001
        Requirement ID: ...
        Title: ...
        Test Type: Non-Functional
        Test Intent: Positive | Negative
        Description: ...
        Expected Behavior: ...
        Evidence: Documented

        ----------------------------------------
        REQUEST-SPECIFIC INSTRUCTIONS:
        {_additional_instructions_block(additional_instructions)}

        If the request-specific instructions say to generate only functional
        output, generate only FUNCTIONAL SCENARIOS and omit the UI SCENARIOS
        and NON-FUNCTIONAL SCENARIOS sections entirely. Otherwise, use the
        format above.
        """,
        requirements_text,
    )


@tool
async def create_test_cases(
    scenarios_text: str,
    additional_instructions: str = "",
) -> str:
    """Turn test scenarios into concise manual test cases ready for a QA demo."""
    return await _generate_text(
        f"""
        You are a senior manual QA test case engineer.

        Convert the supplied scenarios into actionable
        test cases.

        RULES:
        - Preserve the scenario ID in every test case.
        - Prioritize functional workflows over cosmetic checks.
        - Include positive and negative test cases
          when supported by the scenarios.
        - Include clear preconditions and executable steps.
        - Do not invent application behavior.
        - Do not invent error messages or business rules.
        - If the expected result is not documented,
          explicitly state "Requires verification".
        - Do not claim a test has passed.
        - Use only the supplied scenarios.
        - Generate at least one test case for every supplied scenario.
        - Never skip functional scenarios.

        FORMAT:

        Test Case ID: TC-001
        Scenario ID: SC-001
        Title: ...
        Preconditions: ...
        Test Data: ...
        Steps:
        1. ...
        2. ...
        3. ...
        Expected Result: ...
        Evidence Status: Documented | Requires verification

        ----------------------------------------
        REQUEST-SPECIFIC INSTRUCTIONS:
        {_additional_instructions_block(additional_instructions)}

        If the request-specific instructions say to generate only functional
        output, create test cases only for functional scenarios. Do not create
        UI or non-functional test cases.
        """,
        scenarios_text,
    )


@tool
async def generate_test_case_report(runtime: ToolRuntime[BRDContext]) -> str:
    """Run the requirements, scenarios, and test-case workflow for a BRD."""
    brd_text = runtime.context["brd_text"]
    instructions = runtime.context["additional_instructions"]
    requirements = await gather_requirements.ainvoke({"brd_text": brd_text, "additional_instructions": instructions})
    scenarios = await generate_scenarios.ainvoke({"requirements_text": requirements, "additional_instructions": instructions})
    test_cases = await create_test_cases.ainvoke({"scenarios_text": scenarios, "additional_instructions": instructions})

    print(
        f"\n--- Tool output: generate_scenarios ---\n{scenarios}"
        "\n--- End tool output ---",
        flush=True,
    )
    
    return f"BRD TEST SCENARIOS\n\n{scenarios}\n\n{'=' * 40}\n\n{test_cases}"
