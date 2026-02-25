***

# System Prompt & Execution Draft: Multi-Agent Legal Document Generator & CoT Analyzer

**Objective:** Build a LangGraph-native application that uses an Orchestrator-Worker pattern to generate a 50-page legal document, pauses for human input, and then uses a sequential custom Chain of Thought (CoT) pattern to answer queries about the document.

**Tech Stack:** Python 3.11+, `uv` for environment management, `langgraph`, `langchain-google-genai`, `pydantic`.

## 1. Environment & Setup
Initialize the project using `uv`. 
```bash
uv init multi_agent_legal
cd multi_agent_legal
uv add langchain-core langchain-google-genai langgraph pydantic
```
**Environment Variables Required:**
*   `GOOGLE_API_KEY`
*   `LANGSMITH_TRACING="true"` (Highly recommended for observing the Map-Reduce and CoT flows).

## 2. Core Mental Models & Anti-Patterns to Avoid
*   **Anti-Pattern:** Passing the generated 50-page text through the LangGraph State.
    *   **Solution:** State must remain lean. Store only the `file_path` in the State. Nodes will write to and read from the local filesystem directly to prevent checkpointer memory bloat and context window limits.
*   **Anti-Pattern:** Using the default temperature for Gemini 3.0 models.
    *   **Solution:** When initializing `ChatGoogleGenerativeAI` for Gemini 3.0+, you **must** explicitly set `temperature=1.0`. Using legacy defaults like `0.7` can cause infinite loops and degraded reasoning.

## 3. State Schema Design
Implement a single, unified `StateGraph` using Python's `TypedDict`.

```python
from typing import TypedDict, List, Annotated
import operator

class DocumentState(TypedDict):
    # Core Context
    contract_topic: str
    file_path: str
    
    # Map-Reduce State (Agent 1)
    sections_to_write: List[str]  
    completed_sections: Annotated[int, operator.add] 
    
    # QA & CoT State (Agent 2)
    qa_query: str | None
    thought_process: str | None
    final_answer: str | None

class WorkerState(TypedDict):
    """State strictly for the isolated worker nodes executing via Send()"""
    section_topic: str
    file_path: str
```

## 4. LLM Instantiation Logic
Instantiate two separate model configurations using `langchain-google-genai`.

```python
from langchain_google_genai import ChatGoogleGenerativeAI

# Orchestrator & Thinker: Requires high reasoning capacity
pro_llm = ChatGoogleGenerativeAI(
    model="gemini-3-pro-preview",
    temperature=1.0, # Required for Gemini 3+
    max_retries=2
)

# Workers & Synthesizer: Faster, high-volume generation
flash_llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=1.0 # Required for Gemini 3+
)
```

## 5. Node Definitions & Logic

### Agent 1: Document Generation (Orchestrator-Worker)

**Node 1: `planner_node`**
*   **Logic:** Takes `state["contract_topic"]`. Uses `pro_llm.with_structured_output()` to generate a Pydantic list of ~50 detailed legal section titles.
*   **Returns:** `{"sections_to_write": generated_list}`

**Node 2: `writer_node`** (Executes in parallel)
*   **Logic:** Receives `WorkerState` (via the `Send` API). Uses `flash_llm` to write dense, comprehensive legal text for the `section_topic`. Opens `file_path` in append mode (`"a"`) and writes the text. 
*   **Returns:** `{"completed_sections": 1}` (This utilizes the `operator.add` reducer to track completion).

**Node 3: `wait_for_query_node`** (Human-in-the-Loop)
*   **Logic:** Halts execution using LangGraph's native `interrupt()` function to wait for the user to read the document and submit a question.
*   **Pseudo-code:** `query = interrupt("Document generation complete. Please provide your QA query.")`
*   **Returns:** `{"qa_query": query}`

### Agent 2: CoT QA (Sequential)

**Node 4: `thinker_node`**
*   **Logic:** Opens the Markdown file from `state["file_path"]` and reads the content. Injects the document text and `state["qa_query"]` into a strict prompt instructing `pro_llm` to output *only* a detailed, step-by-step reasoning trajectory (the CoT scratchpad).
*   **Returns:** `{"thought_process": raw_reasoning_text}`

**Node 5: `answer_node`**
*   **Logic:** Takes `state["thought_process"]` and `state["qa_query"]`. Uses `flash_llm` (or `pro_llm`) to synthesize the messy CoT reasoning into a clean, professional, final user-facing answer.
*   **Returns:** `{"final_answer": final_text}`

## 6. Graph Construction & Control Flow

Construct the graph utilizing the `Send` API for dynamic fan-out.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langgraph.checkpoint.memory import MemorySaver

def assign_workers(state: DocumentState):
    """Conditional edge: Fan-out to parallel workers based on planned sections."""
    return [Send("writer", {"section_topic": section, "file_path": state["file_path"]}) 
            for section in state["sections_to_write"]]

builder = StateGraph(DocumentState)

# Add all nodes
builder.add_node("planner", planner_node)
builder.add_node("writer", writer_node)
builder.add_node("wait_for_query", wait_for_query_node)
builder.add_node("thinker", thinker_node)
builder.add_node("answer", answer_node)

# Flow 1: Map-Reduce Document Generation
builder.add_edge(START, "planner")
builder.add_conditional_edges("planner", assign_workers, ["writer"])
# LangGraph automatically waits for all 'Send' workers to finish before transitioning
builder.add_edge("writer", "wait_for_query")

# Flow 2: QA & CoT
builder.add_edge("wait_for_query", "thinker")
builder.add_edge("thinker", "answer")
builder.add_edge("answer", END)

# Compilation requires a checkpointer for interrupt() to work
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
```

## 7. Execution Logic
Provide the execution script logic to handle the initial run, the pause, and the resume state.

```python
from langgraph.types import Command

# 1. Initial Invocation
config = {"configurable": {"thread_id": "legal_doc_001"}}
initial_state = {
    "contract_topic": "SaaS Enterprise Master Service Agreement", 
    "file_path": "./output/msa_contract.md",
    "completed_sections": 0
}

# This will run planner -> multiple writers -> pause at wait_for_query
result = graph.invoke(initial_state, config)

# 2. Extract interrupt value (optional, for logging)
print(f"Graph paused. Status: {result['__interrupt__']}")

# 3. Resume Execution with the User Query
user_query = "Does this document include a mutual indemnification clause? Explain the liabilities."

# The graph is resumed by passing a Command object to invoke
final_result = graph.invoke(
    Command(resume=user_query), 
    config
)

print("CoT Process:", final_result["thought_process"])
print("Final Answer:", final_result["final_answer"])
```