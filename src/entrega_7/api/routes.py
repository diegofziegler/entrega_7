from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import HumanMessage

from entrega_7.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    HistoryResponse,
    IngestResponse,
)
from entrega_7.config import settings
from entrega_7.logging_config import agentes_logger, rag_logger
from entrega_7.rag.service import rag_service

router = APIRouter()


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            block if isinstance(block, str) else block.get("text", "")
            for block in content
            if isinstance(block, str) or isinstance(block, dict)
        ]
        return "\n".join(part for part in parts if isinstance(part, str))
    return str(content) if content is not None else ""


def _history_message(message) -> dict[str, str]:
    sender = getattr(message, "name", None) or message.__class__.__name__
    return {"sender": sender, "content": _message_text(getattr(message, "content", ""))}


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request):
    rag_status = getattr(request.app.state, "rag_status", "unavailable")
    return HealthResponse(
        status="ok" if rag_status == "active" else "degraded",
        llm_provider=settings.LLM_PROVIDER,
        rag_status=rag_status,
        checkpointer=getattr(request.app.state, "checkpointer_status", "redis"),
    )


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest, request: Request):
    graph = getattr(request.app.state, "agent_graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="El grafo no está inicializado; verifica Redis.")
    idioma_destino = body.idioma_destino or settings.DEFAULT_LANGUAGE
    agentes_logger.info("API Chat recibida: thread_id=%s, idioma=%s", body.thread_id, idioma_destino)
    graph_config = {"configurable": {"thread_id": body.thread_id}}
    inputs = {"messages": [HumanMessage(content=body.message)], "idioma_destino": idioma_destino}
    try:
        from opentelemetry import trace

        tracer = trace.get_tracer("entrega_7.api")
        with tracer.start_as_current_span("api.chat") as span:
            span.set_attribute("conversation.thread_id", body.thread_id)
            span.set_attribute("response.language", idioma_destino)
            final_state = await graph.ainvoke(inputs, config=graph_config)
        messages = final_state.get("messages", [])
        if not messages:
            raise RuntimeError("El grafo terminó sin producir mensajes.")
        history = [_history_message(message) for message in messages]
        return ChatResponse(
            thread_id=body.thread_id,
            reply=history[-1]["content"],
            idioma_destino=idioma_destino,
            history=history,
        )
    except Exception:
        agentes_logger.exception("Error procesando conversación thread_id=%s", body.thread_id)
        raise HTTPException(status_code=500, detail="No se pudo procesar la conversación.") from None


@router.get("/api/v1/history/{thread_id}", response_model=HistoryResponse)
async def get_history(thread_id: str, request: Request):
    graph = getattr(request.app.state, "agent_graph", None)
    if graph is None:
        raise HTTPException(status_code=503, detail="El grafo no está inicializado; verifica Redis.")
    graph_config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await graph.aget_state(graph_config)
        messages = state.values.get("messages", []) if state and state.values else []
        return HistoryResponse(
            thread_id=thread_id,
            messages=[_history_message(message) for message in messages],
        )
    except Exception:
        agentes_logger.exception("Error recuperando historial thread_id=%s", thread_id)
        raise HTTPException(status_code=500, detail="No se pudo recuperar el historial.") from None


@router.post("/api/v1/rag/ingest", response_model=IngestResponse)
async def ingest_rag_docs(request: Request):
    try:
        count = await rag_service.ingest_directory()
        request.app.state.rag_status = "active"
        return IngestResponse(status="success", chunks_ingested=count, data_dir=settings.DATA_DIR)
    except Exception:
        rag_logger.exception("Error en ingesta RAG desde API.")
        request.app.state.rag_status = "unavailable"
        raise HTTPException(status_code=503, detail="No se pudo ingerir en Pinecone; revisa la configuración.") from None
