from typing import cast
import os
import json
from typing import List, Dict, Optional
import textwrap
import cairosvg
import uuid
from jinja2 import Environment, FileSystemLoader

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables (api key)
load_dotenv()

# --- Configuration ---
MODEL_NAME = "gemini-2.5-flash"
TEMPLATE_DIR = "templates"
TEMPLATE_NAME = "template_panels.html"
BASE_OUTPUT_DIR = "runs"
GUIDELINES_PATH = "mds/svg_guidelines.md"

# --- State Definition (Pydantic) ---

class Character(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(description="Visual description of the character (e.g., stick figure details)")

class PanelCharacter(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(description="Visual description")
    slot: str = Field(description="Position in the panel: 'left' or 'right'")
    facing: str = Field(description="Facing direction: 'left' or 'right'")
    pose: str = Field(description="Physical pose of the character (e.g., 'standing', 'pointing', 'sitting')")
    expression: str = Field(description="Facial expression (e.g., 'happy', 'angry', 'surprised')")
    dialogue: str = Field(description="Text for the speech bubble")

class Panel(BaseModel):
    panel_id: int = Field(description="The panel number")
    background_prompt: str = Field(description="Description of the background scene")
    characters: List[PanelCharacter] = Field(description="List of characters in this panel")

class ComicScript(BaseModel):
    panels: List[Panel] = Field(description="List of 3 panels for the comic")

class AgentState(BaseModel):
    user_prompt: str
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    script: Optional[ComicScript] = None
    assets: Dict[str, str] = Field(default_factory=dict) # Map of character name -> PNG path
    html_output: Optional[str] = None

# --- LLM Initialization ---
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
json_llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.5, response_format={"type": "json_object"})

# --- Helper Functions ---

def load_guidelines():
    if os.path.exists(GUIDELINES_PATH):
        with open(GUIDELINES_PATH, "r") as f:
            return f.read()
    return ""

def svg_to_png(svg_content: str, output_path: str):
    try:
        cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), write_to=output_path)
        return True
    except Exception as e:
        print(f"Error converting SVG to PNG: {e}")
        return False

def wrap_text(text: str, width: int = 25) -> str:
    """Wraps text to a specified width using newlines."""
    return "\n".join(textwrap.wrap(text, width=width))

# --- Nodes ---

def director_node(state: AgentState):
    """
    Generates the comic script in JSON format.
    """
    print(f"--- Director Node ({state.run_id}) ---")
    
    schema_json = json.dumps(ComicScript.model_json_schema(), indent=2)

    prompt_text = f"""
    You are a Comic Director. Generate a JSON script for a 3-panel comic based on the user's request.
    
    User Request: "{state.user_prompt}"
    
    You must output valid JSON that matches the following schema:
    {schema_json}
    
    Constraints:
    - 3 panels exactly.
    - Max 2 characters per panel.
    - Characters must be reused across panels if they are the same person, but you MUST specify a unique 'pose' and 'expression' for each panel to match the story.
    - Slots are strictly 'left' or 'right'.
    - The layout will be 2 panels on top, 1 larger panel centered on the bottom. Plan your storytelling accordingly.
    """
    
    response = json_llm.invoke(prompt_text)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
        
        data = json.loads(content)
        script = ComicScript(**data)
    except Exception as e:
        print(f"Error parsing JSON from Director: {e}")
        script = ComicScript(panels=[])
        
    return {"script": script}

def asset_generator_node(state: AgentState):
    """
    Generates SVGs, converts them to PNGs, and stores paths.
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
    
    # Process every character instance in every panel
    guidelines = load_guidelines()
    new_assets = {}
    
    for p_idx, panel in enumerate(script.panels):
        for c_idx, char in enumerate(panel.characters):
            # Unique ID for this specific instance of the character
            instance_id = f"{p_idx}_{c_idx}"
            
            # Construct a prompt that includes pose and expression
            print(f"Generating asset for: {char.name} (Panel {p_idx}, Slot {char.slot})")
            svg_prompt = f"""
            Generate an SVG for a character named "{char.name}".
            
            Visual Description: {char.visual_desc}
            Pose: {char.pose}
            Expression: {char.expression}
            
            Guidelines:
            {guidelines}
            
            Output ONLY the raw <svg>...</svg> code. No markdown.
            """
            
            # Check if we already have this exact asset (unlikely with dynamic poses, but good for caching if we implemented it)
            # For now, always generate to ensure pose matching
            
            response = llm.invoke(svg_prompt)
            svg_code = response.content.strip()
            
            # Cleanup code blocks
            if "```xml" in svg_code:
                svg_code = svg_code.replace("```xml", "").replace("```", "")
            if "```svg" in svg_code:
                svg_code = svg_code.replace("```svg", "").replace("```", "")
            if "```" in svg_code:
                 svg_code = svg_code.replace("```", "")
    
            # Save SVG
            char_safe_name = char.name.lower().replace(' ', '_')
            svg_filename = f"{char_safe_name}_p{p_idx}_{c_idx}.svg"
            svg_path = os.path.join(images_dir, svg_filename)
            
            with open(svg_path, "w") as f:
                f.write(svg_code)
                
            # Convert to PNG
            png_filename = f"{char_safe_name}_p{p_idx}_{c_idx}.png"
            png_path = os.path.join(images_dir, png_filename)
            
            if svg_to_png(svg_code, png_path):
                print(f"Saved PNG to {png_path}")
                # Store relative path keyed by instance ID
                new_assets[instance_id] = f"images/{png_filename}"
            else:
                print(f"Failed to convert {char.name}, falling back to placeholder.")
                new_assets[instance_id] = "https://placehold.co/400x800/FF0000/FFFFFF/png?text=Error"

    # We don't really need to merge with existing_assets in the same way, 
    # but let's keep it if there were global assets. 
    # Key change: keys are now instance IDs, not names.
    updated_assets = {**existing_assets, **new_assets}
    return {"assets": updated_assets}

def compositor_node(state: AgentState):
    """
    Renders the HTML using Jinja2 template.
    """
    print(f"--- Compositor Node ({state.run_id}) ---")
    if not state.script:
        return {"html_output": "Error: No script generated."}
        
    script = state.script
    assets = state.assets
    
    # Transform script data into the format expected by the template
    panels_data = []
    
    for p_idx, panel in enumerate(script.panels):
        panel_obj = {
            "bg_color": "#f9f9f9", # Default background
            "characters": []
        }
        
        for c_idx, char in enumerate(panel.characters):
            instance_id = f"{p_idx}_{c_idx}"
            char_obj = {
                "name": char.name,
                "image": assets.get(instance_id, ""), # Use instance ID
                "slot": char.slot,
                "facing": char.facing,
                "dialogue": wrap_text(char.dialogue)
            }
            panel_obj["characters"].append(char_obj)
            
        panels_data.append(panel_obj)
        
    # Render Template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    try:
        template = env.get_template(TEMPLATE_NAME)
        html_content = template.render(panels=panels_data)
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
    import sys
    
    user_topic = "Newton explaining gravity to a confused student"
    if len(sys.argv) > 1:
        user_topic = sys.argv[1]
    
    # Init state (generates run_id)
    inputs = AgentState(user_prompt=user_topic)
    run_id = inputs.run_id
    
    print(f"Generating comic for: '{user_topic}'")
    print(f"Run ID: {run_id}")
    
    result = app.invoke(inputs)
    
    output_html = result.get('html_output') if isinstance(result, dict) else result.html_output
    
    # Output File
    run_dir = os.path.join(BASE_OUTPUT_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    output_filename = os.path.join(run_dir, "index.html")
    with open(output_filename, "w") as f:
        if output_html:
            f.write(output_html)
    script = cast(ComicScript, result["script"])
    with open(os.path.join(run_dir, "script.json"), "w") as f:
        f.write(script.model_dump_json(indent=4))
    
    print(f"Comic generated! Open {output_filename} to view.")

