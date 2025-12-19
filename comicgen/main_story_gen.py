
import argparse
import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from comicgen.schemas.definitions import AgentState
from comicgen.nodes import story_director_node, asset_generator_node, story_compositor_node

# Load env variables
load_dotenv()

# --- Graph Construction ---

workflow = StateGraph(AgentState)

workflow.add_node("director", story_director_node)
workflow.add_node("asset_generator", asset_generator_node)
workflow.add_node("compositor", story_compositor_node)

workflow.set_entry_point("director")

workflow.add_edge("director", "asset_generator")
workflow.add_edge("asset_generator", "compositor")
workflow.add_edge("compositor", END)

app = workflow.compile()

# --- Execution ---

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Generate a multi-page comic story.")
    parser.add_argument("prompt", nargs="?", default="A hero's journey", help="The topic for the story")
    parser.add_argument("--fast", action="store_true", help="Fast mode")
    args = parser.parse_args()
    
    user_topic = args.prompt
    
    # Init state
    inputs = AgentState(user_prompt=user_topic, fast_mode=args.fast)
    run_id = inputs.run_id
    
    print(f"Interactive Story Generator")
    print(f"Topic: '{user_topic}'")
    print(f"Run ID: {run_id}")

    result = app.invoke(inputs)

    # Result handling
    # The compositor now writes files to disk, so we just need to confirm completion.
    run_dir = os.path.join("./runs", run_id)
    output_filename = os.path.join(run_dir, "page_1.html")
    
    # Save script for record
    script = result["script"]
    with open(os.path.join(run_dir, "script.json"), "w") as f:
        if isinstance(script, dict):
            f.write(json.dumps(script, indent=4))
        else:
            f.write(script.model_dump_json(indent=4))

    print(f"\n✅ Comic Story Generated!")
    print(f"📂 Output Directory: {run_dir}")
    print(f"👉 Open this file to read: {output_filename}")
