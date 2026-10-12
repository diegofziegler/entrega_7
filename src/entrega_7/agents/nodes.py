import json
from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from src.entrega_7.graph.state import MultiAgentState
from src.entrega_7.agents.llm_factory import get_llm
from src.entrega_7.rag.service import rag_service
from src.entrega_7.config import settings
from src.entrega_7.logging_config import agentes_logger


class RouterSchema(BaseModel):
    next_step: Literal["INVESTIGADOR", "ANALISTA", "FIN"] = Field(
        description="Siguiente agente a ejecutar o FIN si la respuesta está completa."
    )


async def supervisor_node(state: MultiAgentState) -> dict:
    agentes_logger.info("--- NODO SUPERVISOR ---")
    messages = state.get("messages", [])
    last_msg = messages[-1].content if messages else ""

    system_prompt = (
        "Sos el Agente Supervisor. Tu tarea es analizar la conversación y decidir el siguiente paso.\n"
        "Opciones disponibles:\n"
        "- 'INVESTIGADOR': Si se necesita buscar información en la base de datos (RAG).\n"
        "- 'ANALISTA': Si ya se obtuvo la información y se debe redactar la respuesta final en el idioma destino.\n"
        "- 'FIN': Si la pregunta ya ha sido respondida satisfactoriamente.\n"
        "Responde ÚNICAMENTE en formato JSON como: {\"next_step\": \"INVESTIGADOR\" | \"ANALISTA\" | \"FIN\"}"
    )

    llm = get_llm()
    try:
        if hasattr(llm, "with_structured_output"):
            structured_llm = llm.with_structured_output(RouterSchema)
            res = await structured_llm.ainvoke([SystemMessage(content=system_prompt)] + list(messages))
            next_step = res.next_step
        else:
            response = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=f"Último mensaje: {last_msg}")])
            content = response.content.upper()
            if "INVESTIGADOR" in content:
                next_step = "INVESTIGADOR"
            elif "ANALISTA" in content:
                next_step = "ANALISTA"
            else:
                next_step = "FIN"
    except Exception as e:
        agentes_logger.warning(f"Error en decisión de supervisor ({e}). Usando lógica de fallback.")
        has_investigated = any("Módulo RAG" in getattr(m, "content", "") for m in messages)
        has_analyzed = any("Respuesta final" in getattr(m, "content", "") for m in messages)

        if not has_investigated:
            next_step = "INVESTIGADOR"
        elif not has_analyzed:
            next_step = "ANALISTA"
        else:
            next_step = "FIN"

    agentes_logger.info(f"Supervisor decidió siguiente paso: {next_step}")
    return {"next": next_step}


async def investigador_node(state: MultiAgentState) -> dict:
    agentes_logger.info("--- NODO INVESTIGADOR (RAG) ---")
    messages = state.get("messages", [])
    user_query = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_query = msg.content
            break
    if not user_query and messages:
        user_query = messages[0].content

    agentes_logger.info(f"Investigador buscando información para: '{user_query}'")
    docs = await rag_service.search(user_query, k=4)

    if docs:
        retrieved_text = "\n\n".join([f"Source [{doc.metadata.get('source', 'doc')}]: {doc.page_content}" for doc in docs])
        content = f"[Módulo RAG - Información Encontrada]:\n{retrieved_text}"
    else:
        content = "[Módulo RAG]: No se encontró información relevante en los documentos."

    return {
        "messages": [AIMessage(content=content, name="Investigador_RAG")],
        "next": "SUPERVISOR"
    }


async def analista_node(state: MultiAgentState) -> dict:
    agentes_logger.info("--- NODO ANALISTA / SINTETIZADOR ---")
    messages = state.get("messages", [])
    idioma = state.get("idioma_destino") or settings.DEFAULT_LANGUAGE

    system_prompt = (
        f"Sos un analista experto. Tu objetivo es procesar la información obtenida por el Investigador "
        f"y redactar una respuesta clara, completa y estructurada exclusivamente en el idioma: {idioma}."
    )

    llm = get_llm()
    try:
        response = await llm.ainvoke([SystemMessage(content=system_prompt)] + list(messages))
        reply_content = response.content
        if "Respuesta final" not in reply_content:
            reply_content = f"Respuesta final ({idioma}):\n" + reply_content
    except Exception as e:
        agentes_logger.warning(f"Error en analista_node con LLM ({e}). Generando síntesis sintética.")
        rag_info = ""
        for m in messages:
            if "Módulo RAG" in getattr(m, "content", ""):
                rag_info = m.content

        reply_content = (
            f"Respuesta final ({idioma}):\n"
            f"Basado en la información recopilada:\n{rag_info[:500]}..."
        )

    agentes_logger.info(f"Analista generó respuesta en idioma '{idioma}'")
    return {
        "messages": [AIMessage(content=reply_content, name="Analista_Sintetizador")],
        "next": "FIN"
    }
