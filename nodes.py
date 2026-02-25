import os
from typing import List
from langgraph.types import interrupt
from state import DocumentState, WorkerState, SectionOutline, SectionResult
from llm import pro_llm, flash_llm

def planner_node(state: DocumentState):
    """Generates a structured outline of section titles."""
    topic = state["contract_topic"]
    # Using structured output for precision
    structured_llm = pro_llm.with_structured_output(SectionOutline)
    prompt = f"Create a detailed outline for a 50-page legal document on the topic: {topic}. Output ~50 section titles."
    outline: SectionOutline = structured_llm.invoke(prompt)
    return {"sections_to_write": outline.sections}

def writer_node(state: WorkerState):
    """Generates the content for a single section."""
    topic = state["section_topic"]
    index = state["index"]
    prompt = f"""Write a comprehensive, professional legal text for the section: '{topic}'. 

STRICT REQUIREMENTS:
1. Output ONLY the legal text for this section.
2. DO NOT include any preamble, intro, or "Here is the text".
3. DO NOT include any signatures, footer notes, metadata, or JSON-like structures.
4. Output raw text only, no markdown code blocks wrapping the content.
5. Be dense and detailed in formal legalese.
"""
    response = flash_llm.invoke(prompt)
    
    # Extract only the text content, handling potential list of content blocks
    content = response.content
    if isinstance(content, list):
        content = "".join([block.get("text", "") if isinstance(block, dict) else str(block) for block in content])
    elif not isinstance(content, str):
        content = str(content)
        
    # Return the section result to be aggregated later
    return {
        "generated_sections": [{
            "title": topic,
            "content": content,
            "index": index
        }],
        "completed_sections": 1
    }

def aggregator_node(state: DocumentState):
    """Collects all generated sections, sorts them, and writes to disk."""
    # Sort by original index to ensure document order
    sorted_sections = sorted(state["generated_sections"], key=lambda x: x["index"])
    
    file_path = state["file_path"]
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, "w") as f:
        f.write(f"# {state['contract_topic']}\n\n")
        for sec in sorted_sections:
            f.write(f"## {sec['title']}\n\n")
            # Ensure content is a clean string
            content = sec['content']
            f.write(f"{content}\n\n")
            
    return {} # State update handled via file system

def wait_for_query_node(state: DocumentState):
    """Pauses graph for user query."""
    query = interrupt("Document generation complete. Please enter your QA query.")
    return {"qa_query": query}

def thinker_node(state: DocumentState):
    """Generates a concise internal reasoning scratchpad."""
    with open(state["file_path"], "r") as f:
        doc_text = f.read()
    
    query = state["qa_query"]
    prompt = f"""You are an expert legal analyst reviewing the document below.
---
{doc_text}
---
Question: {query}

STRICT INSTRUCTIONS:
1. Provide a internal reasoning scratchpad of ONLY 3-5 short bullet points.
2. Focus on: Where in the document is the answer? What clauses are relevant? What is the core logic for the answer?
3. DO NOT provide the final answer yet.
4. Keep it concise and analytical.
"""

    response = pro_llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "".join([block.get("text", "") if isinstance(block, dict) else str(block) for block in content])

    return {"thought_process": content}

def answer_node(state: DocumentState):
    """Synthesizes the reasoning into a final answer."""
    thought_process = state["thought_process"]
    query = state["qa_query"]
    
    prompt = f"""Based on the following thought process, provide a professional and concise final answer to the user's query.
    
Thought Process:
{thought_process}

User Question: {query}
"""

    response = flash_llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = "".join([block.get("text", "") if isinstance(block, dict) else str(block) for block in content])

    return {"final_answer": content}
