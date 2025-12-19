
import argparse
import os
import json
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from comicgen.schemas.definitions import AgentState
# Import nodes from the new shared module to maintain backward compatibility
from comicgen.nodes import single_page_director_node, asset_generator_node, compositor_node

# Load environment variables
load_dotenv()

# --- Graph Construction ---
# Rebuilding the original graph using the modular nodes

workflow = StateGraph(AgentState)

workflow.add_node("director", single_page_director_node)
workflow.add_node("asset_generator", asset_generator_node)
workflow.add_node("compositor", compositor_node)

workflow.set_entry_point("director")

workflow.add_edge("director", "asset_generator")
workflow.add_edge("asset_generator", "compositor")
workflow.add_edge("compositor", END)

app = workflow.compile()

# --- Execution ---

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Generate a single-page comic.")
    parser.add_argument("prompt", nargs="?", default="Twist ending about a coffee shop", help="The topic for the comic")
    parser.add_argument("--fast", action="store_true", help="Use fast mode (reuse character assets without modification)")
    args = parser.parse_args()
    
    user_topic = args.prompt
    
    # Init state (generates run_id)
    inputs = AgentState(user_prompt=user_topic, fast_mode=args.fast)
    run_id = inputs.run_id
    
    if args.fast:
        print("🚀 FAST MODE ENABLED: Characters will be identical across panels.")

    print(f"Generating single-page comic for: '{user_topic}'")
    print(f"Run ID: {run_id}")

    result = app.invoke(inputs)

    output_html = (
        result.get("html_output") if isinstance(result, dict) else result.html_output
    )

    # Output File
    BASE_OUTPUT_DIR = "./runs"
    run_dir = os.path.join(BASE_OUTPUT_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)

    output_filename = os.path.join(run_dir, "index.html")
    with open(output_filename, "w") as f:
        if output_html:
            f.write(output_html)

    script = result["script"]
    with open(os.path.join(run_dir, "script.json"), "w") as f:
        if isinstance(script, dict):
            f.write(json.dumps(script, indent=4))
        else:
            f.write(script.model_dump_json(indent=4))

    print(f"Comic generated! Open {output_filename} to view.")
