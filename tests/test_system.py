from types import SimpleNamespace

import pytest
import os
from uuid import uuid4
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from entrega_7.api.schemas import ChatRequest
from entrega_7.agents.chains import create_analyst_chain, create_rag_search_chain
from entrega_7.agents.contracts import AnalystOutput, RAGSearchInput, RAGSearchOutput
from entrega_7.main import app
from entrega_7.rag.service import RAGService


class StubGraph:
    def __init__(self):
        self.inputs = []

    async def ainvoke(self, inputs, config):
        self.inputs.append((inputs, config))
        return {"messages": [AIMessage(content=f"Final answer in {inputs['idioma_destino']}", name="Analista_Sintetizador")]}

    async def aget_state(self, config):
        return SimpleNamespace(values={"messages": [AIMessage(content="persisted reply", name="Analista_Sintetizador")]})


@pytest.fixture(autouse=True)
def configure_app_graph():
    app.state.agent_graph = StubGraph()
    app.state.checkpointer_status = "redis"
    app.state.rag_status = "active"


@pytest.mark.asyncio
async def test_health_reports_rag_and_redis_status():
    from entrega_7.api.routes import health_check

    result = await health_check(SimpleNamespace(app=app))
    assert result.status == "ok"
    assert result.rag_status == "active"
    assert result.checkpointer == "redis"


def test_chat_input_schema_rejects_empty_and_extra_fields():
    with pytest.raises(ValueError):
        ChatRequest(message="", thread_id="thread-1")
    with pytest.raises(ValueError):
        ChatRequest(message="hola", thread_id="thread-1", unknown="value")


@pytest.mark.asyncio
async def test_chat_passes_language_and_thread_to_graph():
    from entrega_7.api.routes import chat_endpoint

    result = await chat_endpoint(
        ChatRequest(message="¿Quién fue Kanbun Uechi?", thread_id="session-en", idioma_destino="English"),
        SimpleNamespace(app=app),
    )
    assert "English" in result.reply
    inputs, config = app.state.agent_graph.inputs[0]
    assert inputs["idioma_destino"] == "English"
    assert config["configurable"]["thread_id"] == "session-en"


@pytest.mark.asyncio
async def test_history_has_validated_response_model():
    from entrega_7.api.routes import get_history

    result = await get_history("session-1", SimpleNamespace(app=app))
    assert result.messages[0].content == "persisted reply"


@pytest.mark.asyncio
async def test_hybrid_retriever_fuses_pinecone_dense_and_lexical_results():
    class FakeVectorStore:
        async def asimilarity_search(self, query, k):
            return [Document(page_content="Pinecone dense result", metadata={"source": "dense.md"})]

    service = RAGService()
    lexical = Document(page_content="Kanbun Uechi founded Uechi Ryu karate", metadata={"source": "kanbun.md"})
    service.vectorstore = FakeVectorStore()
    service._documents = [lexical]
    result = await service.search("Kanbun Uechi", k=2)
    assert lexical in result
    assert any(doc.metadata["source"] == "dense.md" for doc in result)


@pytest.mark.asyncio
async def test_langgraph_checkpointer_restores_thread_state():
    class State(TypedDict):
        value: str

    builder = StateGraph(State)
    builder.add_node("set_value", lambda state: {"value": "stored"})
    builder.set_entry_point("set_value")
    builder.add_edge("set_value", END)
    graph = builder.compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "redis-contract"}}
    await graph.ainvoke({"value": "initial"}, config=config)
    saved = await graph.aget_state(config)
    assert saved.values["value"] == "stored"


@pytest.mark.asyncio
async def test_lcel_analyst_chain_returns_pydantic_contract():
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    chain = create_analyst_chain(FakeListChatModel(responses=["The basic techniques train breathing, posture, and strikes."]))
    result = await chain.ainvoke(
        {
            "question": "What do the basic techniques cover?",
            "context": "The basic techniques train breathing, posture, and strikes.",
            "language": "English",
        }
    )
    assert isinstance(result, AnalystOutput)
    assert "breathing" in result.answer


@pytest.mark.asyncio
async def test_lcel_rag_runnable_preserves_async_search_and_pydantic_contract():
    async def fake_search(query: str, k: int):
        assert query == "Uechi-Ryu"
        assert k == 2
        return [Document(page_content="Basic techniques", metadata={"source": "techniques.md"})]

    chain = create_rag_search_chain(fake_search)
    result = await chain.ainvoke(RAGSearchInput(query="Uechi-Ryu", k=2))
    assert isinstance(result, RAGSearchOutput)
    assert result.results == ["Source [techniques.md]: Basic techniques"]


@pytest.mark.asyncio
@pytest.mark.skipif(not os.getenv("TEST_REDIS_URL"), reason="Define TEST_REDIS_URL para probar persistencia real en Redis Stack")
async def test_redis_checkpointer_survives_saver_recreation():
    from langgraph.checkpoint.redis import AsyncRedisSaver

    class State(TypedDict):
        value: str

    builder = StateGraph(State)
    builder.add_node("set_value", lambda state: {"value": "durable"})
    builder.set_entry_point("set_value")
    builder.add_edge("set_value", END)
    config = {"configurable": {"thread_id": f"test-{uuid4()}"}}
    async with AsyncRedisSaver.from_conn_string(os.environ["TEST_REDIS_URL"]) as saver:
        await saver.asetup()
        graph = builder.compile(checkpointer=saver)
        await graph.ainvoke({"value": "initial"}, config=config)
    async with AsyncRedisSaver.from_conn_string(os.environ["TEST_REDIS_URL"]) as saver:
        await saver.asetup()
        graph = builder.compile(checkpointer=saver)
        saved = await graph.aget_state(config)
    assert saved.values["value"] == "durable"
