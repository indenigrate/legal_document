import os
from langgraph.types import Command
from graph import graph

def run_legal_app():
    # 1. Configuration
    thread_id = "legal_doc_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 2. Initial State
    file_path = "./output/legal_document.md"
    initial_state = {
        "contract_topic": "Enterprise SaaS Master Service Agreement",
        "file_path": file_path,
        "completed_sections": 0,
        "generated_sections": [],
        "sections_to_write": []
    }
    
    # Check if file exists to provide better UI feedback
    if os.path.exists(file_path):
        print(f"--- Document already exists at {file_path}. Skipping generation. ---")
    else:
        print("--- Starting Document Generation ---")
    
    # Run until interrupt
    try:
        state = graph.get_state(config)
        if state.next:
            print("Resuming from previous pause...")
        else:
            # This will either run the whole generation OR skip to interrupt
            graph.invoke(initial_state, config)
    except Exception as e:
        # Expected interrupt or error
        pass

    # Re-fetch state to check for interrupt
    state = graph.get_state(config)
    
    if state.next and "wait_for_query" in state.next:
        if not os.path.exists(file_path):
             print("\nWarning: Document generation interrupted or failed to save.")
        
        print(f"\nDocument ready at: {file_path}")
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
        print(f"Graph execution finished or reached unexpected state. Next nodes: {state.next}")

if __name__ == "__main__":
    run_legal_app()
