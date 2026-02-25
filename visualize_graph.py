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
        
        # 1. Try to generate PNG (Requires pygraphviz or mermaid.ink API access)
        print("Generating graph visualization...")
        try:
            png_bytes = graph.get_graph().draw_mermaid_png()
            with open("workflow_graph.png", "wb") as f:
                f.write(png_bytes)
            print("Successfully saved visualization to 'workflow_graph.png'")
        except Exception as e:
            print(f"Could not generate PNG: {e}")
            print("Ensure you have 'pygraphviz' installed or internet access for mermaid.ink.")

        # 2. Always generate Mermaid text as fallback
        print("Generating Mermaid syntax...")
        mermaid_text = graph.get_graph().draw_mermaid()
        with open("workflow_graph.mmd", "w") as f:
            f.write(mermaid_text)
        
        print("Successfully saved Mermaid syntax to 'workflow_graph.mmd'")
        print("
TIP: You can paste the content of 'workflow_graph.mmd' into https://mermaid.live/ to view it online.")

    except ImportError as e:
        print(f"Error: Could not import graph. {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    visualize()
