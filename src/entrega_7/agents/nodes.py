from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from entrega_7.agents.chains import (
    create_analyst_chain,
    create_rag_search_chain,
    create_supervisor_chain,
)
from entrega_7.agents.contracts import AnalystOutput, RAGSearchInput
from entrega_7.agents.llm_factory import get_llm
from entrega_7.config import settings
from entrega_7.graph.state import MultiAgentState
from entrega_7.logging_config import agentes_logger
from entrega_7.rag.service import rag_service


rag_search_chain = create_rag_search_chain(rag_service.search)


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        blocks = []
        for block in content:
            if isinstance(block, str):
                blocks.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                blocks.append(block["text"])
            else:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    blocks.append(text)
        return "\n".join(blocks)
    return str(content) if content is not None else ""


async def supervisor_node(state: MultiAgentState) -> dict:
    agentes_logger.info("--- NODO SUPERVISOR ---")
    messages = list(state.get("messages", []))
    try:
        chain = create_supervisor_chain(get_llm())
        decision = await chain.ainvoke({"messages": messages})
        next_step = decision.next_step
    except Exception as exc:
        agentes_logger.warning(
            "Error en cadena LCEL del supervisor (%s). Usando lógica de fallback.", exc
        )
        contents = [_message_text(message) for message in messages]
        has_investigated = any("Módulo RAG" in content for content in contents)
        has_analyzed = any(
            getattr(message, "name", None) == "Analista_Sintetizador"
            or "Respuesta final" in content
            for message, content in zip(messages, contents)
        )
        if not has_investigated:
            next_step = "INVESTIGADOR"
        elif not has_analyzed:
            next_step = "ANALISTA"
        else:
            next_step = "FIN"

    agentes_logger.info("Supervisor decidió siguiente paso: %s", next_step)
    return {"next": next_step}


async def investigador_node(state: MultiAgentState) -> dict:
    agentes_logger.info("--- NODO INVESTIGADOR (RAG) ---")
    messages = state.get("messages", [])
    user_query = next(
        (_message_text(message) for message in reversed(messages) if isinstance(message, HumanMessage)),
        "",
    )
    if not user_query and messages:
        user_query = _message_text(messages[0])

    agentes_logger.info("Investigador buscando información para: '%s'", user_query)
    search_input = RAGSearchInput(query=user_query, k=4)
    search_output = await rag_search_chain.ainvoke(search_input)

    if search_output.results:
        retrieved_text = "\n\n".join(search_output.results)
        content = f"[Módulo RAG - Información Encontrada]:\n{retrieved_text}"
    else:
        content = "[Módulo RAG]: No se encontró información relevante en los documentos."

    return {
        "messages": [AIMessage(content=content, name="Investigador_RAG")],
        "next": "SUPERVISOR",
    }


async def analista_node(state: MultiAgentState) -> dict:
    agentes_logger.info("--- NODO ANALISTA / SINTETIZADOR ---")
    messages = state.get("messages", [])
    idioma = state.get("idioma_destino") or settings.DEFAULT_LANGUAGE
    question = next(
        (_message_text(message) for message in reversed(messages) if isinstance(message, HumanMessage)),
        "",
    )
    context = next(
        (
            _message_text(message)
            for message in reversed(messages)
            if "Módulo RAG" in _message_text(message)
        ),
        "No se encontró información relevante en los documentos.",
    )

    try:
        chain = create_analyst_chain(get_llm())
        answer = await chain.ainvoke(
            {"question": question, "context": context, "language": idioma}
        )
    except Exception as exc:
        agentes_logger.warning(
            "Error en cadena LCEL del analista (%s). Generando síntesis de respaldo.", exc
        )
        fallback = context[:500].rstrip()
        if len(context) > len(fallback):
            fallback = fallback[: max(1, settings.ANALYST_MAX_OUTPUT_CHARS - 3)].rstrip() + "..."
        if not fallback:
            fallback = "No se pudo generar una respuesta."
        max_chars = settings.ANALYST_MAX_OUTPUT_CHARS
        if len(fallback) > max_chars:
            fallback = fallback[: max_chars - 3].rstrip() + "..."
        answer = AnalystOutput(answer=fallback)

    agentes_logger.info("Analista generó respuesta en idioma '%s'", idioma)
    return {
        "messages": [AIMessage(content=answer.answer, name="Analista_Sintetizador")],
        "next": "FIN",
    }
