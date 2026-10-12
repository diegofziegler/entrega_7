from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM Settings
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_NAME: str = "gemini-1.5-flash"
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL_NAME: str = "llama-3.3-70b-versatile"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"

    # Vector DB & Pinecone
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX_NAME: str = "entrega-7-index"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    VECTORSTORE_DIR: str = "./vectorstore"
    DATA_DIR: str = "./data"
    LOG_DIR: str = "./log"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Telemetry
    PHOENIX_COLLECTOR_ENDPOINT: str = "http://localhost:6006"
    PHOENIX_PROJECT_NAME: str = "orquestador-multi-agente"

    # Language
    DEFAULT_LANGUAGE: str = "Español"


settings = Settings()
