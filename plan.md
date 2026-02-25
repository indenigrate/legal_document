Final, production-ready system design utilizing the `gemini-3-pro-preview` and `gemini-3-flash-preview` models, managing massive text generation via Map-Reduce, and implementing explicit CoT.

---

### 1. The Mental Model

Your system relies on two distinct graph patterns combined into a single, cohesive workflow:
1.  **The Orchestrator-Worker (Map-Reduce):** Agent 1 plans the 50-page document and spins up parallel "Writer" nodes using LangGraph's `Send` API to overcome LLM output limits.
2.  **The Sequential CoT (Think → Act):** Agent 2 reads the generated document and explicitly drafts a reasoning scratchpad before generating the final user-facing response.
3.  **Human-in-the-Loop:** A native `interrupt()` pauses the graph between Agent 1 and Agent 2 to collect the user's query.

### 2. State Design (The Lean Schema)

We keep the State lean. The 50-page text lives on the disk, not in the state, preventing checkpointer bloat and token waste.

```python
from typing import TypedDict, List, Annotated
import operator

class DocumentState(TypedDict):
    contract_topic: str
    file_path: str
    
    # Map-Reduce State
    sections_to_write: List[str]  
    completed_sections: Annotated[int, operator.add] 
    
    # QA & Custom CoT State
    qa_query: str | None
    thought_process: str | None
    final_answer: str | None
```

*Note: The `WorkerState` for the `Send` API will just need the specific `section_name` and the `file_path`.*

### 3. Node Definitions

#### Agent 1: Document Generation (Orchestrator-Worker)

*   **Node 1: `planner_node`**
    *   **Model:** `gemini-3-pro-preview` (Best for complex planning).
    *   **Action:** Takes `contract_topic`. Uses `.with_structured_output()` to generate an outline of ~50 detailed section headers.
    *   **State Update:** Writes to `sections_to_write`.
*   **Node 2: `writer_node` (Parallel Worker)**
    *   **Model:** `gemini-3-flash-preview` (Faster and cheaper for high-volume text generation).
    *   **Action:** Receives a specific section topic. Generates the legal text. Uses standard Python file I/O (`open(filepath, "a")`) to append the text to the markdown file.
    *   **State Update:** Returns `{"completed_sections": 1}` to increment the reducer.
*   **Node 3: `wait_for_query_node`**
    *   **Action:** Uses LangGraph's `interrupt()` to halt execution. 
    *   **Code:** `query = interrupt("Document complete. Please enter your QA query.")`
    *   **State Update:** Writes the user's response to `qa_query`.

#### Agent 2: Custom CoT QA

Because Gemini models boast a 1M-2M token context window, you can safely load the entire 50-page markdown file (~30k tokens) directly into memory within these nodes.

*   **Node 4: `thinker_node` (The Custom CoT)**
    *   **Model:** `gemini-3-pro-preview` 
    *   **Action:** Reads the `.md` file from disk. Takes the `qa_query`. The prompt explicitly instructs the model to act as a legal analyst, read the document, and output a detailed, step-by-step reasoning trajectory (e.g., "Step 1: Locate indemnification clauses. Step 2: Analyze liabilities...").
    *   **State Update:** Writes the raw reasoning to `thought_process`.
*   **Node 5: `answer_node`**
    *   **Model:** `gemini-3-flash-preview` (or Pro).
    *   **Action:** Takes the `thought_process` and the `qa_query` (and optionally the document text again). The prompt instructs it to synthesize the messy reasoning scratchpad into a clean, professional, final answer for the user.
    *   **State Update:** Writes to `final_answer`.

### 4. Graph Control Flow (Wiring it up)

Here is the cleaner, LangGraph-native pattern for wiring this together, specifically utilizing the `Send` API for your parallel writers.

```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

def assign_workers(state: DocumentState):
    """Conditional edge to fan-out workers based on the generated outline."""
    return [Send("writer", {"section": s, "file_path": state["file_path"]}) 
            for s in state["sections_to_write"]]

builder = StateGraph(DocumentState)

# Add Nodes
builder.add_node("planner", planner_node)
builder.add_node("writer", writer_node)
builder.add_node("wait_for_query", wait_for_query_node)
builder.add_node("thinker", thinker_node)
builder.add_node("answer", answer_node)

# Add Edges
builder.add_edge(START, "planner")

# Fan-out: Planner goes to multiple parallel writers
builder.add_conditional_edges("planner", assign_workers, ["writer"])

# Fan-in: LangGraph automatically waits for all 'Send' workers to finish
# before crossing this edge to the next node.
builder.add_edge("writer", "wait_for_query")

# QA Flow
builder.add_edge("wait_for_query", "thinker")
builder.add_edge("thinker", "answer")
builder.add_edge("answer", END)

# Compile with a checkpointer (Required for interrupt() to work)
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
```

### 5. Crucial Gemini 3.0 Configuration Note

When initializing `ChatGoogleGenerativeAI` for Gemini 3.0 models (`gemini-3-pro-preview` or `gemini-3-flash-preview`), **you must explicitly set `temperature=1.0`**. 

Google's API best practices dictate that using the legacy default temperature of `0.7` with Gemini 3.0+ can cause infinite loops, degraded reasoning performance, and failure on complex tasks.

```python
from langchain_google_genai import ChatGoogleGenerativeAI

# The Orchestrator / Thinker
pro_llm = ChatGoogleGenerativeAI(
    model="gemini-3-pro-preview",
    temperature=1.0 # CRITICAL for Gemini 3+
)

# The Writers / Synthesizer
flash_llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    temperature=1.0 # CRITICAL for Gemini 3+
)
```

### Summary of Execution
1.  **Initialize:** `uv run python main.py`
2.  **Kickoff:** You invoke the graph with a thread ID, the `contract_topic`, and a target `file_path`.
3.  **Map-Reduce:** The graph plans the document, spawns 50 parallel instances of Gemini Flash to write the sections, and stitches them into your Markdown file.
4.  **Pause:** The graph hits `interrupt()` and saves state to the checkpointer.
5.  **Resume:** You call `graph.invoke(Command(resume={"qa_query": "Is there a non-compete?"}), config)`.
6.  **CoT & Answer:** The `thinker` node reads the 50 pages and generates the reasoning. The `answer` node formats it, and the graph completes.