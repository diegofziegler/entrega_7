from langgraph.graph import END, StateGraph

from entrega_7.agents.nodes import analista_node, investigador_node, supervisor_node
from entrega_7.graph.state import MultiAgentState


def route_supervisor(state: MultiAgentState) -> str:
    return {
        "INVESTIGADOR": "investigador",
        "ANALISTA": "analista",
    }.get(state.get("next"), END)


def create_agent_graph(checkpointer):
    """Build the graph with an explicitly supplied, lifespan-managed checkpointer."""
    workflow = StateGraph(MultiAgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("investigador", investigador_node)
    workflow.add_node("analista", analista_node)
    workflow.set_entry_point("supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {"investigador": "investigador", "analista": "analista", END: END},
    )
    workflow.add_edge("investigador", "supervisor")
    workflow.add_edge("analista", END)
    return workflow.compile(checkpointer=checkpointer)
