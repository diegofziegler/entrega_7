from typing import Annotated, TypedDict, Sequence, Optional, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class MultiAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    next: Optional[str]
    idioma_destino: str
