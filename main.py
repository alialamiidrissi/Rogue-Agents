import os
import json
import typing
from typing import List, Dict, Optional, Annotated
import operator

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from dotenv import load_dotenv

# Load environment variables (api key)
load_dotenv()

# --- Configuration ---
# You can allow the user to override this via env var or input
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
    panel_id: int = Field(description="The panel number")
    background_prompt: str = Field(description="Description of the background scene")
    characters: List[PanelCharacter] = Field(description="List of characters in this panel")

class ComicScript(BaseModel):
    panels: List[Panel] = Field(description="List of 3 panels for the comic")

class AgentState(BaseModel):
    user_prompt: str
    script: Optional[ComicScript] = None
    assets: Dict[str, str] = Field(default_factory=dict) # Map of character name -> SVG implementation key/code
    html_output: Optional[str] = None

# --- LLM Initialization ---
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
# For JSON structure, we can usually still use json mode or structured output
json_llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.5, response_format={"type": "json_object"})

# --- Nodes ---

def director_node(state: AgentState):
    """
    Generates the comic script in JSON format.
    """
    print("--- Director Node ---")
    
    # Get the JSON schema from the Pydantic model to guide the LLM
    schema_json = json.dumps(ComicScript.model_json_schema(), indent=2)

    prompt_text = f"""
    You are a Comic Director. Generate a JSON script for a 3-panel comic based on the user's request.
    
    User Request: "{state.user_prompt}"
    
    You must output valid JSON that matches the following schema:
    {schema_json}
    
    Constraints:
    - 3 panels exactly.
    - Max 2 characters per panel.
    - Characters must be reused across panels if they are the same person.
    - Slots are strictly 'left', 'center', or 'right'.
    """
    
    response = json_llm.invoke(prompt_text)
    
    try:
        content = response.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
        
        data = json.loads(content)
        # Validate with Pydantic
        script = ComicScript(**data)
    except Exception as e:
        print(f"Error parsing JSON from Director: {e}")
        # Fallback empty script
        script = ComicScript(panels=[])
        
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
    for panel in script.panels:
        for char in panel.characters:
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
        
    # Merge
    updated_assets = {**existing_assets, **new_assets}
    return {"assets": updated_assets}

def compositor_node(state: AgentState):
    """
    Generates the final HTML using the script and assets.
    """
    print("--- Compositor Node ---")
    if not state.script:
        return {"html_output": "Error: No script generated."}
        
    script = state.script
    assets = state.assets
    
    # Convert Pydantic model to dict for JSON serialization in prompt
    script_dict = script.model_dump()
    
    prompt_text = f"""
    You must create a single HTML file for a webcomic.
    
    ### Inputs
    
    1. **Script**:
    {json.dumps(script_dict, indent=2)}
    
    2. **Character Assets (SVGs)**:
    {json.dumps(assets, indent=2)}
    
    ### Requirements
    
    1. **Layout**:
       - Use CSS Grid or Flexbox to create a 3-panel horizontal layout (or vertical on mobile).
       - Each panel must have a distinct border/frame.
       
    2. **Character Placement**:
       - Use the 'slot' ('left', 'center', 'right') to position characters absolutely within the panel.
       - 'Left' slot: left: 5%, width: 40%
       - 'Right' slot: right: 5%, width: 40%
       - 'Center' slot: left: 30%, width: 40%
       - If 'facing' is 'left', apply `transform: scaleX(-1)` to the SVG container.
       - Embed the SVGs directly into the HTML (or use <defs> and <use>).
       
    3. **Dialogue**:
       - Create speech bubbles near the characters.
       - Use simple CSS for speech bubbles (oval white background, black border).
       
    4. **Styling**:
       - Make it look clean and comic-like.
       - Add a title "Paper Doll Comic Generated by Gemini".
       
    Output ONLY the raw HTML code. Do not include markdown code blocks.
    """
    
    response = llm.invoke(prompt_text)
    html_content = response.content.strip()
    
    if "```html" in html_content:
        html_content = html_content.replace("```html", "").replace("```", "")
        
    return {"html_output": html_content}

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
        
    print(f"Generating comic for: {user_topic}")
    
    # Initial state
    inputs = AgentState(user_prompt=user_topic)
    
    result = app.invoke(inputs)
    
    # 'result' will be the final state (dict or object depending on langgraph version/config, usually dict in invoke)
    # If using Pydantic state, result might be the final Pydantic object or dict. 
    # LangGraph compile().invoke() typically returns a dict representation of state.
    
    output_html = result.get('html_output') if isinstance(result, dict) else result.html_output
    
    output_filename = "output.html"
    with open(output_filename, "w") as f:
        if output_html:
            f.write(output_html)
        
    print(f"Comic generated! Open {output_filename} to view.")
