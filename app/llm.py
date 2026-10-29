from langchain_groq import ChatGroq
from .config import get_settings


def get_llm(model: str | None = None):
    settings = get_settings()
    selected_model = model or settings.groq_model
    model_kwargs = {"parallel_tool_calls": False}

    # GPT-OSS uses `include_reasoning`; other Groq reasoning models require a
    # supported reasoning format when function tools are attached.
    if selected_model.startswith("openai/gpt-oss-"):
        model_kwargs["include_reasoning"] = False

    return ChatGroq(
        api_key=settings.groq_api_key,
        model=selected_model,
        temperature=0.1,
        reasoning_effort="low",
        max_tokens=3500,
        model_kwargs=model_kwargs,
    )

def get_vision_llm():
    settings = get_settings()

    return ChatGroq(
        api_key=settings.groq_api_key,
        model="qwen/qwen3.8-27b",
        temperature=0,
        max_tokens=3500,
        max_retries=2,
    )