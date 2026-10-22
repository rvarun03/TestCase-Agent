from langchain_groq import ChatGroq
from .config import get_settings


def get_llm():
    settings = get_settings()

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.1
    )