from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatRequest(StrictSchema):
    message: str = Field(min_length=1, max_length=20_000, examples=["¿Quién fue Kanbun Uechi?"])
    thread_id: str = Field(min_length=1, max_length=200, pattern=r"^[\w.:-]+$")
    idioma_destino: str | None = Field(default=None, min_length=2, max_length=64)


class HistoryMessage(StrictSchema):
    sender: str
    content: str


class ChatResponse(StrictSchema):
    thread_id: str
    reply: str
    idioma_destino: str
    history: list[HistoryMessage]


class HistoryResponse(StrictSchema):
    thread_id: str
    messages: list[HistoryMessage]


class IngestResponse(StrictSchema):
    status: Literal["success"]
    chunks_ingested: int = Field(ge=0)
    data_dir: str


class HealthResponse(StrictSchema):
    status: Literal["ok", "degraded"]
    llm_provider: str
    rag_status: Literal["active", "unavailable"]
    checkpointer: Literal["redis"]
