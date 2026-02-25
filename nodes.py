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
    prompt = f"Write a comprehensive, professional legal text for the section: '{topic}'. Be dense and detailed."
    response = flash_llm.invoke(prompt)
    
    # Return the section result to be aggregated later
    return {
        "generated_sections": [{
            "title": topic,
            "content": response.content,
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
            f.write(f"{sec['content']}\n\n")
            
    return {} # State update handled via file system

def wait_for_query_node(state: DocumentState):
    """Pauses graph for user query."""
    query = interrupt("Document generation complete. Please enter your QA query.")
    return {"qa_query": query}

def thinker_node(state: DocumentState):
    """Generates Chain of Thought reasoning."""
    with open(state["file_path"], "r") as f:
        doc_text = f.read()
    
    query = state["qa_query"]
    prompt = f"""You are an expert legal analyst. Below is a legal document.
---
{doc_text}
---
Question: {query}

Think step-by-step through the document to find the relevant clauses and analyze them for the final answer. 
Output your detailed thought process ONLY. No final answer yet."""

    response = pro_llm.invoke(prompt)
    return {"thought_process": response.content}

def answer_node(state: DocumentState):
    """Synthesizes the reasoning into a final answer."""
    thought_process = state["thought_process"]
    query = state["qa_query"]
    
    prompt = f"""Based on the following thought process, provide a professional and concise final answer to the user's query.
    
Thought Process:
{thought_process}

User Question: {query}"""

    response = flash_llm.invoke(prompt)
    return {"final_answer": response.content}
