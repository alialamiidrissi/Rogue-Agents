import os
import json
import typing
from typing import List, Dict, Optional, Annotated
import operator
import re
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import uuid

from dotenv import load_dotenv

# Load environment variables (api key)
load_dotenv()

# --- Configuration ---
MODEL_NAME = "gemini-2.5-flash"

# --- State Definition (Pydantic) ---

class Character(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(description="Visual description of the character (e.g., stick figure details)")

class PanelCharacter(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(description="Visual description")
    slot: str = Field(description="Position in the panel: 'left', 'center', or 'right'")
    facing: str = Field(description="Facing direction: 'left' or 'right'")
    dialogue: str = Field(description="Text for the speech bubble")

class Panel(BaseModel):
    background_prompt: str = Field(description="Description of the background scene")
    characters: List[PanelCharacter] = Field(description="List of characters in this panel")

class AgentState(BaseModel):
    user_prompt: str
    folder_name: str
    script: Optional[Panel] = None
    assets: Dict[str, str] = Field(default_factory=dict) # Map of character name -> SVG implementation key/code
    html_output: Optional[str] = None

# --- LLM Initialization ---
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
json_llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.5, response_format={"type": "json_object"})

# --- Nodes ---

def director_node(state: AgentState):
    """
    Generates the comic script in JSON format.
    """
    print("--- Director Node ---")
    
    # Get the JSON schema from the Pydantic model to guide the LLM
    schema_json = json.dumps(Panel.model_json_schema(), indent=2)

    prompt_text = f"""
    You are a Comic Director. Generate a JSON script for a single full-page comic panel based on the user's request.
    
    User Request: "{state.user_prompt}"
    
    You must output valid JSON that matches the following schema:
    {schema_json}
    
    Constraints:
    - Max 3 possible characters in the scene.
    - Slots are strictly 'left', 'center', or 'right'.
    - The content should be dense enough to justify a full page.
    - Keep dialogue strictly under 15 words to prevent overcrowding and text overlap.
    """
    
    response = json_llm.invoke(prompt_text)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
        
        data = json.loads(content)
        # Validate with Pydantic
        script =  Panel(**data)
    except Exception as e:
        print(f"Error parsing JSON from Director: {e}")
        # Fallback empty script
        script = Panel(background_prompt="", characters=[])
        
    # Return dict for state update
    return {"script": script}

def asset_generator_node(state: AgentState):
    """
    Generates SVGs for characters found in the script.
    Optimizes by reusing existing assets.
    """
    print("--- Asset Generator Node ---")
    
    if not state.script:
        print("No script found.")
        return {"assets": state.assets}

    script = state.script
    existing_assets = state.assets
    
    # Identify unique characters
    unique_characters = {}
    for char in script.characters:
            name = char.name
            if name not in existing_assets and name not in unique_characters:
                unique_characters[name] = char.visual_desc
    
    new_assets = {}
    
    for name, desc in unique_characters.items():
        print(f"Generating asset for: {name}")
        svg_prompt = f"""
        Generate a simple, clean SVG code for a character named "{name}".
        Visual Description: {desc}
        
        Constraints:
        - The SVG should be a standalone <svg> string.
        - ViewBox should be standard (e.g., 0 0 100 100 or similar).
        - Use simple shapes (circle for head, lines for body) as a 'Paper Doll' style.
        - Transparent background.
        - NO Markdown formatting. Just the raw <svg>...</svg> code.
        """
        response = llm.invoke(svg_prompt)
        svg_code = response.content.strip()
        if "```xml" in svg_code:
            svg_code = svg_code.replace("```xml", "").replace("```", "")
        if "```svg" in svg_code:
            svg_code = svg_code.replace("```svg", "").replace("```", "")
            
        new_assets[name] = svg_code
        
        # Save SVG to file
        with open(os.path.join(state.folder_name, f"{name}.svg"), "w") as f:
            f.write(svg_code)
        
    # Merge
    updated_assets = {**existing_assets, **new_assets}
    return {"assets": updated_assets}

def parse_svg_dimensions(svg_code):
    """
    Extracts width, height, and viewBox from SVG code using regex.
    """
    # Simple regex implementation
    viewbox_re = re.search(r'viewBox=["\']([^"\']+)["\']', svg_code)
    width_re = re.search(r'width=["\']([^"\']+)["\']', svg_code)
    height_re = re.search(r'height=["\']([^"\']+)["\']', svg_code)
    
    info = {
        "aspect_ratio": "unknown",
    }
    
    if viewbox_re:
        info['viewBox'] = viewbox_re.group(1)
        # Try to calculate aspect ratio from viewBox
        try:
            vb_parts = [float(x) for x in info['viewBox'].split()]
            if len(vb_parts) == 4:
                w, h = vb_parts[2], vb_parts[3]
                info['aspect_ratio'] = f"{w/h:.2f}"
        except:
            pass
            
    if width_re: info['width'] = width_re.group(1)
    if height_re: info['height'] = height_re.group(1)
        
    return info

def compositor_node(state: AgentState):
    """
    Generates the final HTML using the script and assets.
    """
    print("--- Compositor Node ---")
    if not state.script:
        return {"html_output": "Error: No script generated."}
        
    script = state.script
    assets = state.assets
    
    # 1. Parse SVGs to get dimensions/metadata for the LLM
    # This ensures the LLM knows the shape of the assets without seeing the full code.
    asset_metadata = {}
    for name, svg_code in assets.items():
        dims = parse_svg_dimensions(svg_code)
        asset_metadata[name] = {
            "dimensions": dims,
            "marker": f"__INSERT_SVG_{name.upper().replace(' ', '_')}__"
        }
    
    # Convert Pydantic model to dict for JSON serialization in prompt
    script_dict = script.model_dump()
    print(asset_metadata)
    
    prompt_text = f"""
    You must create a single HTML file for a webcomic that consists of one large full-page panel.
    
    ### Inputs
    
    1. **Script**:
    {json.dumps(script_dict, indent=2)}
    
    2. **Available Character Assets**:
    {json.dumps(asset_metadata, indent=2)}
    
    ### Requirements
    
    1. **Layout**:
       - Create a single container that fills most of the screen (e.g., 90vh height, centered).
       - It should look like a large poster or a single splash page comic panel.
       - distinct thick border.
       
    2. **Character Placement**:
       - Use the 'slot' ('left', 'center', 'right') to position characters absolutely within the panel.
       - If 'facing' is 'left', apply `transform: scaleX(-1)` to the SVG container.
       - RESPECT THE ASPECT RATIO provided in the asset metadata.
       
    3. **Asset Injection**:
       - Do NOT invent new SVGs.
       - Put the exact valid marker string (e.g. `__INSERT_SVG_NAME__`) inside the character container div.
       - The post-processing step will replace this marker with the actual SVG code.
       
    4. **Dialogue & Layout**:
       - Create readable speech bubbles.
       - CRITICAL: Place bubbles to avoid overlapping characters or other bubbles. 
       - STRATEGY: Place bubbles in the empty space away from the center convergence. For example, if a character is on the Left, anchor the bubble to the top-left or left side. If Right, anchor top-right.
       - Font Sizing: Use a smaller, concise font (e.g., 14px or 0.9rem) to ensures text fits inside the bubble. 
       - Constrain bubble max-width to roughly 25-30% of the container width to avoid walls of text.
       - Use simple CSS for speech bubbles (oval white background, black border, slight shadow).
       
    5. **Styling**:
       - Make it look clean and comic-like.
       - Add a title "Single Panel Comic" at the top.
       
    Output ONLY the raw HTML code. Do not include markdown code blocks.
    """
    
    response = llm.invoke(prompt_text)
    html_template = response.content.strip()
    
    if "```html" in html_template:
        html_template = html_template.replace("```html", "").replace("```", "")
        
    # --- Template Filling ---
    print("Filling template with actual SVGs...")
    final_html = html_template
    
    for name, meta in asset_metadata.items():
        marker = meta['marker']
        svg_code = assets[name]
        
        if marker in final_html:
             final_html = final_html.replace(marker, svg_code)
        else:
            print(f"Warning: Marker {marker} not found in generated HTML.")
            # Fallback: Try to inject by ID if marker missing? 
            # For now, just warn.
            
    return {"html_output": final_html}

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
        
    print(f"Generating single-panel comic for: {user_topic}")
    
    file_name = uuid.uuid4().hex
    os.makedirs(file_name, exist_ok=True)

    # Initial state
    inputs = AgentState(user_prompt=user_topic, folder_name=file_name)
    
    result = app.invoke(inputs)
    
    output_html = result.get('html_output') if isinstance(result, dict) else result.html_output
    
    output_filename = os.path.join(file_name, "output_single.html")
    with open(output_filename, "w") as f:
        if output_html:
            f.write(output_html)

    # Also save the script for debugging
    if result.get('script'):
        script_data = result['script'].model_dump() if hasattr(result['script'], 'model_dump') else result['script']
        with open(os.path.join(file_name, "script.json"), "w") as f:
            json.dump(script_data, f, indent=4)
        
    print(f"Comic generated! Open {output_filename} to view.")
