from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.entrega_7.graph.state import MultiAgentState
from src.entrega_7.agents.nodes import supervisor_node, investigador_node, analista_node
from src.entrega_7.config import settings
from src.entrega_7.logging_config import agentes_logger


def route_supervisor(state: MultiAgentState) -> str:
    next_step = state.get("next")
    if next_step == "INVESTIGADOR":
        return "investigador"
    elif next_step == "ANALISTA":
        return "analista"
    else:
        return END


def create_agent_graph(checkpointer=None):
    workflow = StateGraph(MultiAgentState)

    # Define Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("investigador", investigador_node)
    workflow.add_node("analista", analista_node)

    # Set Entry Point
    workflow.set_entry_point("supervisor")

    # Conditional Edges from Supervisor
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "investigador": "investigador",
            "analista": "analista",
            END: END
        }
    )

    # Return to Supervisor after worker execution
    workflow.add_edge("investigador", "supervisor")
    workflow.add_edge("analista", END)

    if checkpointer is None:
        try:
            from langgraph.checkpoint.postgres import PostgresSaver # Optional
        except ImportError:
            pass

        # Try Redis Checkpointer or Fallback MemorySaver
        try:
            from langgraph.checkpoint.redis.aio import AsyncRedisSaver
            # checkpointer = AsyncRedisSaver.from_conn_info(host=..., port=...)
            # We use MemorySaver as a reliable default fallback if Redis connection fails
            checkpointer = MemorySaver()
        except Exception as e:
            agentes_logger.info(f"Usando MemorySaver como checkpointer: {e}")
            checkpointer = MemorySaver()

    compiled = workflow.compile(checkpointer=checkpointer)
    return compiled

agent_graph = create_agent_graph()
