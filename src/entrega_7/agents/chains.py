from collections.abc import Awaitable, Callable

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableLambda
from entrega_7.agents.contracts import AnalystOutput, RAGSearchInput, RAGSearchOutput, RouterSchema
from entrega_7.config import settings


SUPERVISOR_PROMPT = """Sos el Agente Supervisor. Decide cuál es el siguiente paso según el estado de la conversación.
Opciones:
- INVESTIGADOR: hace falta buscar conocimiento en el RAG.
- ANALISTA: ya hay resultados del RAG y se necesita redactar la respuesta final.
- FIN: la solicitud ya fue respondida.
Elige INVESTIGADOR antes de ANALISTA cuando todavía no haya resultados RAG para la pregunta actual."""

ANALYST_PROMPT = """Sos un analista experto. Responde la pregunta del usuario usando solamente el contexto recuperado.
Escribe exclusivamente en {language}, con claridad y en no más de 250 palabras.
No repitas literalmente los documentos ni agregues información que no esté respaldada por el contexto.
Si el contexto no contiene la respuesta, dilo claramente."""


def create_supervisor_chain(llm):
    """Compose conversation routing as an async-capable LCEL chain."""
    prompt = ChatPromptTemplate.from_messages(
        [("system", SUPERVISOR_PROMPT), MessagesPlaceholder(variable_name="messages")]
    )
    return prompt | llm.with_structured_output(RouterSchema)


def _message_to_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            else:
                text = getattr(block, "text", None)
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()
    return str(content).strip() if content is not None else ""


def _validate_analyst_output(message: BaseMessage) -> AnalystOutput:
    text = _message_to_text(message)
    if not text:
        raise ValueError("El LLM devolvió una respuesta vacía.")

    max_chars = settings.ANALYST_MAX_OUTPUT_CHARS
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return AnalystOutput(answer=text)


def create_analyst_chain(llm):
    """Compose prompt, model, and Pydantic validation into one LCEL chain."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANALYST_PROMPT),
            ("human", "Pregunta del usuario:\n{question}\n\nContexto RAG:\n{context}"),
        ]
    )
    return prompt | llm | RunnableLambda(_validate_analyst_output)


def create_rag_search_chain(
    search: Callable[..., Awaitable[list]],
):
    """Adapt the async hybrid retriever to a typed LCEL Runnable boundary."""
    async def retrieve(payload: RAGSearchInput) -> RAGSearchOutput:
        request = RAGSearchInput.model_validate(payload)
        documents = await search(request.query, k=request.k)
        return RAGSearchOutput(
            results=[
                f"Source [{document.metadata.get('source', 'doc')}]: {document.page_content}"
                for document in documents
            ]
        )

    return RunnableLambda(retrieve).with_types(
        input_type=RAGSearchInput,
        output_type=RAGSearchOutput,
    )
