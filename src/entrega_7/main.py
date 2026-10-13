from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.entrega_7.api.routes import router
from src.entrega_7.rag.service import rag_service
from src.entrega_7.logging_config import agentes_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    agentes_logger.info("Iniciando aplicación FastAPI (Entrega 7)...")
    # Auto-ingest docs if data directory exists
    try:
        await rag_service.ingest_directory()
    except Exception as e:
        agentes_logger.warning(f"Error en auto-ingesta inicial RAG: {e}")
    yield
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
    uvicorn.run("src.entrega_7.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
