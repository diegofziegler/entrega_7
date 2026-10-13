import pytest
from httpx import AsyncClient, ASGITransport
from src.entrega_7.main import app
from src.entrega_7.rag.service import rag_service


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "llm_provider" in data


@pytest.mark.asyncio
async def test_rag_ingest_and_search():
    count = await rag_service.ingest_directory()
    assert count > 0

    results = await rag_service.search("Kanbun Uechi", k=2)
    assert len(results) > 0
    assert any("Kanbun" in doc.page_content for doc in results)


@pytest.mark.asyncio
async def test_chat_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "message": "¿Quién fue Kanbun Uechi?",
            "thread_id": "test-session-unit",
            "idioma_destino": "Español"
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test-session-unit"
        assert data["idioma_destino"] == "Español"
        assert "reply" in data
        assert len(data["history"]) > 0


@pytest.mark.asyncio
async def test_chat_multilingual_english():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "message": "¿Cuáles son las técnicas básicas de Uechi-Ryu?",
            "thread_id": "test-session-en",
            "idioma_destino": "Inglés"
        }
        response = await client.post("/api/v1/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["idioma_destino"] == "Inglés"


@pytest.mark.asyncio
async def test_get_history_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First send a message to populate state
        payload = {
            "message": "Hola, prueba de historial",
            "thread_id": "test-history-thread",
            "idioma_destino": "Español"
        }
        await client.post("/api/v1/chat", json=payload)

        # Retrieve history
        response = await client.get("/api/v1/history/test-history-thread")
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test-history-thread"
        assert len(data["messages"]) >= 1
