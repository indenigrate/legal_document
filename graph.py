from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver

from state import DocumentState
from nodes import (
    planner_node, 
    writer_node, 
    aggregator_node, 
    wait_for_query_node, 
    thinker_node, 
    answer_node
)

def assign_workers(state: DocumentState):
    """Conditional edge: fan-out to writers."""
    return [
        Send("writer", {"section_topic": s, "index": i}) 
        for i, s in enumerate(state["sections_to_write"])
    ]

# Initialize Graph
builder = StateGraph(DocumentState)

# Add Nodes
builder.add_node("planner", planner_node)
builder.add_node("writer", writer_node)
builder.add_node("aggregator", aggregator_node)
builder.add_node("wait_for_query", wait_for_query_node)
builder.add_node("thinker", thinker_node)
builder.add_node("answer", answer_node)

# Define Flow
builder.add_edge(START, "planner")
builder.add_conditional_edges("planner", assign_workers, ["writer"])
builder.add_edge("writer", "aggregator")
builder.add_edge("aggregator", "wait_for_query")
builder.add_edge("wait_for_query", "thinker")
builder.add_edge("thinker", "answer")
builder.add_edge("answer", END)

# Checkpointer for interrupt support
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
