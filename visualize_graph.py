import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())

# Load environment variables
load_dotenv()

def visualize():
    print("--- Initializing Legal Graph for Visualization ---")
    
    try:
        from graph import graph
        
        # We use draw_mermaid_png() because it produces a superior, professional diagram 
        # compared to the standard graphviz output, and it handles complex 
        # parallel nodes (Map-Reduce) more cleanly.
        print("Generating high-quality workflow diagram (PNG)...")
        try:
            # This generates a PNG via the Mermaid engine
            png_bytes = graph.get_graph().draw_mermaid_png()
            with open("workflow_graph.png", "wb") as f:
                f.write(png_bytes)
            print("\nSUCCESS: Saved 'workflow_graph.png'")
            print("This PNG shows the Orchestrator-Worker (Map-Reduce) and Sequential CoT patterns.")
        except Exception as e:
            print(f"\nFAILED to generate PNG: {e}")
            print("Falling back to ASCII (Check your internet connection for Mermaid PNG generation):")
            print(graph.get_graph().draw_ascii())

    except ImportError as e:
        print(f"Error: Could not import graph. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    visualize()
