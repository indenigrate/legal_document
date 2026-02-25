import os
from langgraph.types import Command
from graph import graph

def run_legal_app():
    # 1. Configuration
    thread_id = "legal_doc_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 2. Initial State
    initial_state = {
        "contract_topic": "Enterprise SaaS Master Service Agreement",
        "file_path": "./output/legal_document.md",
        "completed_sections": 0,
        "generated_sections": [],
        "sections_to_write": []
    }
    
    print("--- Starting Document Generation ---")
    
    # Run until interrupt
    # If the thread already exists, we might need to check current state
    # For a fresh run, we invoke with initial_state
    try:
        # Check if we are already interrupted
        state = graph.get_state(config)
        if state.next:
            print("Resuming from previous pause...")
        else:
            graph.invoke(initial_state, config)
    except Exception as e:
        # If it's the first time and it interrupts, it might raise or return
        pass

    # Re-fetch state to check for interrupt
    state = graph.get_state(config)
    
    if state.next and "wait_for_query" in state.next:
        print(f"\nDocument generated at: {initial_state['file_path']}")
        user_query = input("\nPlease enter your legal question about the document: ")
        
        print("\n--- Starting CoT Analysis ---")
        # Resume the graph with the user's query
        final_state = graph.invoke(
            Command(resume=user_query),
            config
        )
        
        print("\n--- Reasoning Scratchpad ---")
        print(final_state.get("thought_process"))
        
        print("\n--- Final Answer ---")
        print(final_state.get("final_answer"))
    else:
        print("Graph execution finished or failed.")

if __name__ == "__main__":
    run_legal_app()
