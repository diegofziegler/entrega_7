from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ChatRequest(BaseModel):
    message: str = Field(..., json_schema_extra={"example": "¿Quién fue Kanbun Uechi?"})
    thread_id: str = Field(..., json_schema_extra={"example": "session-123"})
    idioma_destino: Optional[str] = Field("Español", json_schema_extra={"example": "Francés"})


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    idioma_destino: str
    history: List[Dict[str, Any]]


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    data_dir: str


class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    rag_status: str
    checkpointer: str
