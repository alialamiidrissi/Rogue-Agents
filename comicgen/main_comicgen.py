from typing import cast
import os
import json
import textwrap
import requests

import argparse

from jinja2 import Environment, FileSystemLoader

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from dotenv import load_dotenv
from comicgen.schemas.comicgen import ComicCharacter
from comicgen.schemas.definitions import AgentState, ComicScript

# Load environment variables (api key)
load_dotenv()


# --- Configuration ---
MODEL_NAME = "gemini-2.5-flash"
TEMPLATE_DIR = "comicgen/templates"
TEMPLATE_NAME = "template_panels.html"
BASE_OUTPUT_DIR = "./runs"
GUIDELINES_PATH = "comicgen/mds/svg_guidelines.md"




# --- LLM Initialization ---
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
json_llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME, temperature=0.5, response_format={"type": "json_object"}
).with_retry(exponential_jitter_params={"initial": 3})

# --- Helper Functions ---


def load_guidelines():
    if os.path.exists(GUIDELINES_PATH):
        with open(GUIDELINES_PATH, "r") as f:
            return f.read()
    return ""





def wrap_text(text: str, width: int = 25) -> str:
    """Wraps text to a specified width using newlines."""
    return "\n".join(textwrap.wrap(text, width=width))


# --- Nodes ---


def director_node(state: AgentState):
    """
    Generates the comic script in JSON format.
    """
    print(f"--- Director Node ({state.run_id}) ---")

    prompt_text = f"""
    You are a Comic Director. Generate a script for a 3-panel comic based on the user's request.

    User Request: "{state.user_prompt}"

    For background_layer:
    - type: Choose from 'sky', 'indoor', 'space', 'abstract'
    - color: A CSS color name or hex code (e.g., 'blue', '#87CEEB')
    - gradient: Optional gradient description (e.g., 'linear-gradient(to bottom, #87CEEB, white)')

    Constraints:
    - 3 panels exactly.
    - Max 2 characters per panel.
    - Characters must be reused across panels if they are the same person, but you MUST specify a unique 'pose' and 'expression' for each panel to match the story.
    - Slots are strictly 'left' or 'right'.
    - The layout will be 2 panels on top, 1 larger panel centered on the bottom. Plan your storytelling accordingly.
    
    Compatible Characters (Visual descriptions should map to these):
    1. "Aavatar": Generic human (customizable hair/clothes).
    2. "Ethan": Man with beard & glasses.
    3. "Bean": Living coffee mug.
    4. "Deenuova" / "Deynuovo": Specific visually distinct humans.
    5. "Bill" (Man in suit) / "Sophie" (Old grandma style woman): Front-view only.
    """

    structured_llm = add_retry(llm.with_structured_output(ComicScript.model_json_schema(), method="json_schema"))
    try:
        response = structured_llm.invoke(prompt_text)
        if isinstance(response, dict):
            script = ComicScript(**response)
        else:
            script = response
    except Exception as e:
        print(f"Error parsing JSON from Director: {e}")
        script = ComicScript(panels=[])

    return {"script": script}


def asset_generator_node(state: AgentState):
    """
    Generates SVGs, converts them to PNGs, and stores paths.
    Now implements caching to reuse character assets for consistency.
    """
    print(f"--- Asset Generator Node ({state.run_id}) ---")

    if not state.script:
        print("No script found.")
        return {"assets": state.assets}

    # Setup Run Directories
    run_dir = os.path.join(BASE_OUTPUT_DIR, state.run_id)
    images_dir = os.path.join(run_dir, "images")
    os.makedirs(images_dir, exist_ok=True)

    script = state.script
    existing_assets = state.assets

    # Function to fetch asset
    def fetch_comicgen_asset(url: str, output_path: str) -> bool:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                print(f"Error fetching asset: {response.status_code}")
                return False
        except Exception as e:
            print(f"Error fetching asset: {e}")
            return False

    # Process every character instance in every panel
    # guidelines = load_guidelines()  <-- No longer needed
    new_assets = {}

    # Initial consistency context message
    consistency_context = """
    You are a ComicGen API Configurator.
    Your goal is to configure characters that are CONSISTENT across panels.
    Use the provided schema to generate the configuration JSON.
    """
    # We will process panel by panel
    for p_idx, panel in enumerate(script.panels):
        for c_idx, char in enumerate(panel.characters):
            # Unique ID
            instance_id = f"{p_idx}_{c_idx}"
            print(f"Generating asset for: {char.name} (Panel {p_idx}, Slot {char.slot})")
            
            schema_json = json.dumps(ComicCharacter.model_json_schema(), indent=2)

            # Construct Prompt
            prompt = f"""
            {consistency_context}
            
            Target Character: "{char.name}"
            Visual Description: "{char.visual_desc}"
            
            Panel Context:
            - Pose: {char.pose}
            - Expression: {char.expression}
            - Slot: {char.slot} (Position in panel)
            
            Available Characters & Rules:
            1. "aavatar": Best for general purpose.
            2. "ethan": Man with beard/glasses. Supports 'back', 'side', 'straight'.
            3. "bean": Coffee mug.
            4. "bill" (Man in suit), "sophie" (Old grandma style woman): Front view only.
            
            If this character appeared in previous panels, try to keep the 'style' parameters consistent (same hair, clothes, etc.), but change the 'pose' and 'emotion'.
            
            You MUST output valid JSON matching this schema:
            {schema_json}
            """
            
            url = ""
            current_prompt = prompt
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    # Invoke LLM to get configuration
                    response = json_llm.invoke(current_prompt)
                    content = response.content
                    if "```json" in content:
                        content = content.replace("```json", "").replace("```", "")
                    
                    data = json.loads(content)
                    comic_char = ComicCharacter(**data)
                    url = comic_char.to_url()
                    
                    print(f"   -> Generated URL: {url}")
                    break
                    
                except Exception as e:
                    print(f"   -> Error generating config for {char.name} (Attempt {attempt+1}): {e}")
                    # Append error to prompt for correction
                    current_prompt += f"\n\nFailed to parse JSON. Error: {e}. Please correct the JSON schema and try again."
                
            # Download Asset
            if url:
                 # Check/Create filename
                char_safe_name = char.name.lower().replace(' ', '_')
                png_filename = f"{char_safe_name}_p{p_idx}_{c_idx}.png"
                png_path = os.path.join(images_dir, png_filename)
                
                if fetch_comicgen_asset(url, png_path):
                     print(f"   -> Saved PNG to {png_path}")
                     new_assets[instance_id] = f"images/{png_filename}"
                else:
                    new_assets[instance_id] = "https://placehold.co/400x800/FF0000/FFFFFF/png?text=FetchError"
            else:
                 new_assets[instance_id] = "https://placehold.co/400x800/FF0000/FFFFFF/png?text=ConfigError"

    updated_assets = {**existing_assets, **new_assets}
    return {"assets": updated_assets}


def add_retry(llm):
    return llm.with_retry(exponential_jitter_params={"initial": 3})

def compositor_node(state: AgentState):
    """
    Renders the HTML using Jinja2 template, embedding images as base64.
    """
    print(f"--- Compositor Node ({state.run_id}) ---")
    if not state.script:
        return {"html_output": "Error: No script generated."}

    script = state.script
    assets = state.assets


    llm_with_retry = add_retry(llm)

    # Generate title and subtitle
    try:
        title_prompt = f"""
        Create a fun cartoon title and subtitle for a comic explaining: "{state.user_prompt}"

        Title: Should be catchy and cartoon-like, e.g., "The Wacky World of Photosynthesis"
        Subtitle: Explain the main characters, e.g., "Starring Alex and Sam on their plant adventure!"

        Output format:
        Title: [title]
        Subtitle: [subtitle]
        """
        title_response = llm_with_retry.invoke(title_prompt)
        title_text = title_response.content.strip()
        # Parse
        title = "Amazing Cartoon Explanation"
        subtitle = "Featuring fun characters!"
        for line in title_text.split('\n'):
            if line.startswith('Title:'):
                title = line.replace('Title:', '').strip()
            elif line.startswith('Subtitle:'):
                subtitle = line.replace('Subtitle:', '').strip()
    except Exception as e:
        print(f"Error generating title: {e}")
        title = "Fun Cartoon Explanation"
        subtitle = "Starring our heroes!"

    # Transform script data into the format expected by the template
    panels_data = []

    for p_idx, panel in enumerate(script.panels):
        # Start with the panel's dict representation
        panel_data = panel.model_dump()

        # Update characters
        for c_idx, char_data in enumerate(panel_data["characters"]):
            instance_id = f"{p_idx}_{c_idx}"
            image_path = assets.get(instance_id, "")
            char_data["image"] = image_path
            
            # Apply text wrapping
            if "dialogue" in char_data:
                char_data["dialogue"] = wrap_text(char_data["dialogue"], width=20) # Adjust width as needed
                print(f"   -> Wrapped dialogue: {char_data['dialogue']}")

        panels_data.append(panel_data)

    # Render Template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    try:
        template = env.get_template(TEMPLATE_NAME)
        html_content = template.render(panels=panels_data, comic_title=title, comic_subtitle=subtitle)
        return {"html_output": html_content}
    except Exception as e:
        return {"html_output": f"Error rendering template: {e}"}


# --- Graph Construction ---

workflow = StateGraph(AgentState)

workflow.add_node("director", director_node)
workflow.add_node("asset_generator", asset_generator_node)
workflow.add_node("compositor", compositor_node)

workflow.set_entry_point("director")

workflow.add_edge("director", "asset_generator")
workflow.add_edge("asset_generator", "compositor")
workflow.add_edge("compositor", END)

app = workflow.compile()

# --- Execution ---

if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description="Generate a comic.")
    parser.add_argument("prompt", nargs="?", default="Twist ending about a coffee shop", help="The topic for the comic")
    parser.add_argument("--fast", action="store_true", help="Use fast mode (reuse character assets without modification)")
    args = parser.parse_args()
    
    user_topic = args.prompt
    
    # Init state (generates run_id)
    inputs = AgentState(user_prompt=user_topic, fast_mode=args.fast)
    run_id = inputs.run_id
    
    if args.fast:
        print("🚀 FAST MODE ENABLED: Characters will be identical across panels.")

    print(f"Generating comic for: '{user_topic}'")
    print(f"Run ID: {run_id}")

    result = app.invoke(inputs)

    output_html = (
        result.get("html_output") if isinstance(result, dict) else result.html_output
    )

    # Output File
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

    # Generate graph visualization
    try:
        graph_png = app.get_graph().draw_mermaid_png()
        graph_filename = os.path.join(run_dir, "graph.png")
        with open(graph_filename, "wb") as f:
            f.write(graph_png)
        print(f"📊 Graph visualization saved to {graph_filename}")
    except AttributeError as e:
        print(f"Error: draw_mermaid_png method not available: {e}")
        # Fallback: generate mermaid string
        try:
            mermaid_code = app.get_graph().draw_mermaid()
            mermaid_filename = os.path.join(run_dir, "graph.mmd")
            with open(mermaid_filename, "w") as f:
                f.write(mermaid_code)
            print(f"📊 Mermaid graph saved to {mermaid_filename}")
        except Exception as e2:
            print(f"Error generating mermaid: {e2}")
    except Exception as e:
        print(f"Error generating graph visualization: {e}")

    print(f"Comic generated! Open {output_filename} to view.")
