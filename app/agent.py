"""A single-agent starting point: learn this before adding more agents."""

from langchain_groq import ChatGroq

from .config import get_settings
from .models import GenerateResponse

SYSTEM_PROMPT = """You are a careful QA engineer. Create practical manual test
cases from the supplied BRD. Include happy-path, validation/error, and boundary
cases when supported by the BRD. Do not invent behaviour. Every case needs clear,
observable expected results. Return at most 10 high-value test cases."""


def get_agent():
    settings = get_settings()
    model = ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1,
    )
    return model.with_structured_output(GenerateResponse)


async def generate_test_cases(brd_text: str) -> GenerateResponse:
    return await get_agent().ainvoke([
        ("system", SYSTEM_PROMPT),
        ("human", f"BRD:\n{brd_text}"),
    ])
