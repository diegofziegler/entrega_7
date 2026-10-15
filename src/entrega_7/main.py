from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from entrega_7.api.routes import router
from entrega_7.rag.service import rag_service
from entrega_7.logging_config import agentes_logger
from entrega_7.graph.builder import create_agent_graph
from entrega_7.config import settings
from entrega_7.telemetry import setup_telemetry, shutdown_telemetry


@asynccontextmanager
async def lifespan(app: FastAPI):
    agentes_logger.info("Iniciando aplicación FastAPI (Entrega 7)...")
    setup_telemetry()
    from langgraph.checkpoint.redis import AsyncRedisSaver

    async with AsyncRedisSaver.from_conn_string(settings.REDIS_URL) as checkpointer:
        await checkpointer.asetup()
        app.state.agent_graph = create_agent_graph(checkpointer)
        app.state.checkpointer_status = "redis"
        app.state.rag_status = "unavailable"
        try:
            await rag_service.initialize()
            await rag_service.ingest_directory()
            app.state.rag_status = "active"
        except Exception:
            agentes_logger.exception("RAG no disponible; se requiere Pinecone y un índice configurado.")
        try:
            yield
        finally:
            shutdown_telemetry()
            agentes_logger.info("Cerrando aplicación FastAPI...")


app = FastAPI(
    title="Sistema de Inteligencia de Grado de Producción (Entrega 7)",
    description="API para orquestación de agentes con supervisor, RAG avanzado, persistencia y trazabilidad.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


def main():
    import uvicorn
    uvicorn.run("entrega_7.main:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
