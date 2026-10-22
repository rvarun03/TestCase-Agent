from langchain.agents import create_agent
from langchain_groq import ChatGroq

from ..config import get_settings
from ..models import RequirementAnalysis


SYSTEM_PROMPT = """
You are a Requirement Analysis Agent.

Read the supplied Business Requirements Document.

Extract:
- Functional requirements
- Business rules
- User roles and permissions
- Input validations
- Missing or ambiguous details

Rules:
- Assign unique IDs like REQ-001, REQ-002.
- Do not invent requirements.
- Extract requirements based on their meaning.
- Return the requirements in the defined structure.
"""


def get_requirement_agent():

    settings = get_settings()

    llm = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1
    )

    agent = create_agent(
        model=llm,
        tools=[],
        system_prompt=SYSTEM_PROMPT,
        response_format=RequirementAnalysis
    )

    return agent

async def analyze_requirements(
    brd_text: str
) -> RequirementAnalysis:

    agent = get_requirement_agent()

    result = await agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": brd_text
            }
        ]
    })

    return result["structured_response"]