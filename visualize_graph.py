import os
import sys

# Ensure the current directory is in the path so graph.py can be imported
sys.path.append(os.getcwd())

from graph import graph

def generate_graph_png(output_filename="updated_workflow_graph.png"):
    print(f"Generating updated graph flow and saving to {output_filename}...")
    
    try:
        # Get the drawable representation of the compiled graph
        drawable_graph = graph.get_graph()
        
        # Generate the PNG image bytes using Mermaid
        png_bytes = drawable_graph.draw_mermaid_png()
        
        # Write the bytes to a file
        with open(output_filename, "wb") as f:
            f.write(png_bytes)
            
        print(f"SUCCESS: Successfully saved the new graph to '{output_filename}'.")
        
    except Exception as e:
        print(f"FAILED to generate PNG. Error: {e}")
        print("Fallback to ASCII representation:")
        print(drawable_graph.draw_ascii())

if __name__ == "__main__":
    generate_graph_png()