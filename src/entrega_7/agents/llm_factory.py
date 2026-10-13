from langchain_core.language_models.chat_models import BaseChatModel
from langchain_community.chat_models import FakeListChatModel
from src.entrega_7.config import settings
from src.entrega_7.logging_config import agentes_logger


def get_llm() -> BaseChatModel:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini" and settings.GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            agentes_logger.info("Inicializando LLM Gemini")
            return ChatGoogleGenerativeAI(
                model=settings.GEMINI_MODEL_NAME,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.3,
            )
        except Exception as e:
            agentes_logger.warning(f"Error al inicializar Gemini ({e}). Usando fallback.")

    elif provider == "groq" and settings.GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            agentes_logger.info("Inicializando LLM Groq")
            return ChatGroq(
                model_name=settings.GROQ_MODEL_NAME,
                groq_api_key=settings.GROQ_API_KEY,
                temperature=0.3,
            )
        except Exception as e:
            agentes_logger.warning(f"Error al inicializar Groq ({e}). Usando fallback.")

    elif provider == "openai" and settings.OPENAI_API_KEY:
        try:
            from langchain_openai import ChatOpenAI
            agentes_logger.info("Inicializando LLM OpenAI")
            return ChatOpenAI(
                model_name=settings.OPENAI_MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.3,
            )
        except Exception as e:
            agentes_logger.warning(f"Error al inicializar OpenAI ({e}). Usando fallback.")

    # Resilient Mock / Fallback LLM when no API keys or providers work
    agentes_logger.info("Usando Mock LLM de fallback")

    class SmartMockLLM(FakeListChatModel):
        def __init__(self):
            responses = [
                "SUPERVISOR: INVESTIGADOR",
                "He consultado la base de datos y encontré información sobre Karate Uechi-Ryu y sus maestros.",
                "SUPERVISOR: ANALISTA",
                "Basándome en la información recuperada, respondo a tu consulta de manera completa y detallada.",
                "SUPERVISOR: FIN",
            ]
            super().__init__(responses=responses)

    return SmartMockLLM()
