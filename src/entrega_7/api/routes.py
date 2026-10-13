from fastapi import APIRouter, HTTPException, BackgroundTasks
from langchain_core.messages import HumanMessage
from src.entrega_7.api.schemas import ChatRequest, ChatResponse, IngestResponse, HealthResponse
from src.entrega_7.graph.builder import agent_graph
from src.entrega_7.rag.service import rag_service
from src.entrega_7.config import settings
from src.entrega_7.logging_config import agentes_logger, rag_logger

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        llm_provider=settings.LLM_PROVIDER,
        rag_status="active" if rag_service.vectorstore else "inactive",
        checkpointer="LangGraph Checkpointer (Memory/Redis)"
    )


@router.post("/api/v1/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    agentes_logger.info(f"API Chat recibida: thread_id={request.thread_id}, idioma={request.idioma_destino}")

    config = {"configurable": {"thread_id": request.thread_id}}
    inputs = {
        "messages": [HumanMessage(content=request.message)],
        "idioma_destino": request.idioma_destino or settings.DEFAULT_LANGUAGE
    }

    try:
        final_state = await agent_graph.ainvoke(inputs, config=config)
        messages = final_state.get("messages", [])

        reply = "No se obtuvo respuesta."
        if messages:
            reply = messages[-1].content

        formatted_history = [
            {
                "sender": getattr(m, "name", m.__class__.__name__),
                "content": m.content
            }
            for m in messages
        ]

        return ChatResponse(
            thread_id=request.thread_id,
            reply=reply,
            idioma_destino=request.idioma_destino,
            history=formatted_history
        )
    except Exception as e:
        agentes_logger.error(f"Error procesando conversación API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/v1/history/{thread_id}")
async def get_history(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await agent_graph.aget_state(config)
        if not state or not state.values:
            return {"thread_id": thread_id, "messages": []}

        messages = state.values.get("messages", [])
        formatted_history = [
            {
                "sender": getattr(m, "name", m.__class__.__name__),
                "content": m.content
            }
            for m in messages
        ]
        return {"thread_id": thread_id, "messages": formatted_history}
    except Exception as e:
        agentes_logger.error(f"Error recuperando historial para {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/rag/ingest", response_model=IngestResponse)
async def ingest_rag_docs(background_tasks: BackgroundTasks = None):
    rag_logger.info("Solicitud de ingesta RAG iniciada desde API.")
    try:
        count = await rag_service.ingest_directory()
        return IngestResponse(
            status="success",
            chunks_ingested=count,
            data_dir=settings.DATA_DIR
        )
    except Exception as e:
        rag_logger.error(f"Error en ingesta RAG desde API: {e}")
        raise HTTPException(status_code=500, detail=str(e))
