from typing import Literal

from pydantic import BaseModel, Field


class RouterSchema(BaseModel):
    next_step: Literal["INVESTIGADOR", "ANALISTA", "FIN"] = Field(
        description="Siguiente agente a ejecutar o FIN si la respuesta está completa."
    )


class RAGSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    k: int = Field(default=4, ge=1, le=20)


class RAGSearchOutput(BaseModel):
    results: list[str]


class AnalystOutput(BaseModel):
    answer: str = Field(min_length=1, strict=True)
