# Legal Document Generator and QA System

A robust legal document generation and analysis system built with LangGraph and Gemini 3.0 models. It uses a Map-Reduce architecture for large-scale document generation and a Chain-of-Thought (CoT) reasoning loop for legal QA.

## Setup

### Prerequisites
- Python 3.10+
- A Google Gemini API Key

### Install uv (Recommended)
If you do not have `uv` installed, run:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Dependencies
Using `uv`:
```bash
uv sync
```

Using `pip`:
```bash
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the root directory and add your API key:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

## How to Run

Execute the main application:
```bash
uv run python main.py
```
Or with standard Python:
```bash
python main.py
```

### Generating a New Document
The system checks for an existing document before starting generation. To generate a new legal document, delete the current `output/legal_document.md` file.

### Changing the Topic
To change the topic of the document generation, update the `initial_state` in `main.py`.

## System Design

### Project Flow
1. **Planning (Orchestrator):** The `planner_node` (using Gemini Pro) generates a high-level outline with ~50 section titles.
2. **Writing (Parallel Workers):** The system uses LangGraph's `Send` API to trigger multiple `writer_node` instances in parallel. Each worker (using Gemini Flash) writes a specific section.
3. **Aggregation:** The `aggregator_node` collects all sections, sorts them by their original index, and writes the final markdown file to disk.
4. **Interrupt:** The graph pauses to wait for a user query regarding the generated document.
5. **Reasoning (CoT):** Upon receiving a query, the `thinker_node` reads the entire document from disk and generates a 3-5 point reasoning scratchpad.
6. **Final Answer:** The `answer_node` synthesizes the reasoning into a professional legal response.

### Why it is Robust
- **Disk-Based State:** Large document content is stored on disk rather than in the LangGraph state. This prevents state bloat, reduces token waste, and ensures the system can handle massive documents without hitting memory or state limits.
- **Map-Reduce Architecture:** By splitting document generation into parallel tasks, the system overcomes LLM output token limits and significantly reduces total generation time.
- **Human-in-the-Loop:** Native `interrupt` support allows the system to pause and resume, making it suitable for interactive workflows.

### Why Vector DB and RAG are Not Needed
- **Large Context Window:** Gemini 3.0 models support 1M+ token context windows. This allows the system to load the entire 50-page document (~30k-50k tokens) directly into the prompt for QA.
- **Superior Reasoning:** By providing the full context, the LLM has access to every clause and nuance without the retrieval errors or "lost in the middle" issues often associated with RAG and vector search.
- **Complexity Reduction:** Eliminating a Vector DB removes the need for embedding generation, indexing, and complex retrieval logic, making the system simpler to maintain and more accurate for small to medium-sized legal corpuses.
