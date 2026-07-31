"""
LLM wrapper around Google Gemini (via LangChain).

Kept intentionally thin: one function that returns a ready-to-use
chat model, with a clear error message if the API key is missing.
"""

from langchain_google_genai import ChatGoogleGenerativeAI

from src import config


def get_llm(temperature: float = 0.0) -> ChatGoogleGenerativeAI:
    """
    Returns a configured Gemini chat model instance.

    Raises:
        ValueError: if GOOGLE_API_KEY is not set.
    """
    api_key = config.get_google_api_key()

    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY not found. Add it to your .env file "
            "(see .env.example)."
        )

    return ChatGoogleGenerativeAI(
        model=config.LLM_MODEL,
        google_api_key=api_key,
        temperature=temperature,
        # Gemini 3+ models "think" before answering by default, which adds
        # latency/cost and returns extra non-text content blocks. "low" keeps
        # answer quality for a Q&A task while avoiding that overhead. Older
        # dated models ignore this field harmlessly.
        thinking_level="low",
    )


# Run this file directly to sanity-check that credentials + the model
# name are valid, without going through the full Streamlit app.
if __name__ == "__main__":
    try:
        llm = get_llm()
        test = llm.invoke("Reply with the single word: OK")
        print(f"Model '{config.LLM_MODEL}' responded: {test.content!r}")
    except Exception as exc:  # noqa: BLE001 - top-level diagnostic script
        print(f"LLM check failed: {exc}")
