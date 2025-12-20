
import argparse
import os
import glob
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv

from comicgen.schemas.definitions import AgentState, ComicScript
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
    if args.fast:
        # Find latest run
        list_of_files = glob.glob('./runs/*') 
        if not list_of_files:
            print("❌ No previous runs found. Cannot use fast mode.")
            exit(1)
            
        latest_run_dir = max(list_of_files, key=os.path.getmtime)
        run_id = os.path.basename(latest_run_dir)
        print(f"🚀 Fast Mode: Loading from run {run_id}")
        
        # Load script
        script_path = os.path.join(latest_run_dir, "script.json")
        try:
            with open(script_path, "r") as f:
                script_data = json.load(f)
                script = ComicScript(**script_data)
        except FileNotFoundError:
             print("❌ script.json not found in latest run.")
             exit(1)

        # Reconstruct Assets Map
        assets = {}
        images_dir = os.path.join(latest_run_dir, "images")
        
        # We perform a "best effort" recovery of asset paths based on the script structure
        # Logic mirrors asset_generator_node naming convention
        for p_idx, panel in enumerate(script.panels):
            for c_idx, char in enumerate(panel.characters):
                instance_id = f"{p_idx}_{c_idx}"
                char_safe_name = char.name.lower().replace(' ', '_')
                expected_filename = f"{char_safe_name}_p{p_idx}_{c_idx}.png"
                # Check if file exists to be safe
                if os.path.exists(os.path.join(images_dir, expected_filename)):
                    assets[instance_id] = f"images/{expected_filename}" 
        
        inputs = AgentState(user_prompt=user_topic, fast_mode=True, run_id=run_id, script=script, assets=assets)

    else:
        inputs = AgentState(user_prompt=user_topic, fast_mode=False)
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
