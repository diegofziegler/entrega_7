from langchain_core.language_models.chat_models import BaseChatModel

from entrega_7.config import settings


def get_llm() -> BaseChatModel:
    """Return the configured provider; fail clearly instead of silently mocking production."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL_NAME,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.3,
            max_output_tokens=2048,
        )
    if provider == "groq" and settings.GROQ_API_KEY:
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=settings.GROQ_MODEL_NAME,
            api_key=settings.GROQ_API_KEY,
            temperature=0.3,
            max_tokens=2048,
        )
    if provider == "openai" and settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.3,
            max_tokens=2048,
        )
    raise RuntimeError(f"Proveedor LLM '{provider}' sin credenciales o no soportado; configura su API key en .env.")
