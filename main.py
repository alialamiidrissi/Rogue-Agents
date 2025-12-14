from typing import cast
import os
import json
from typing import List, Dict, Optional
import textwrap
import cairosvg
import uuid
import argparse
from jinja2 import Environment, FileSystemLoader

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables (api key)
load_dotenv()

# --- Configuration ---
MODEL_NAME = "tngtech/deepseek-r1t2-chimera:free"  # Free DeepSeek R1 model on OpenRouter
TEMPLATE_DIR = "templates"
TEMPLATE_NAME = "template_panels.html"
BASE_OUTPUT_DIR = "runs"
GUIDELINES_PATH = "mds/svg_guidelines.md"

# --- State Definition (Pydantic) ---


class Character(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(
        description="Visual description of the character (e.g., stick figure details)"
    )


class GridPosition(BaseModel):
    x: int = Field(description="X coordinate (0-8) in 9x9 grid", ge=0, le=8)
    y: int = Field(description="Y coordinate (0-8) in 9x9 grid", ge=0, le=8)

class PanelElement(BaseModel):
    type: str = Field(description="Type of element: 'equation', 'icon', 'symbol', 'text'")
    content: str = Field(description="The actual content to render")
    position: GridPosition = Field(description="Position in 9x9 grid")
    size: str = Field(description="Size category: 'small', 'medium', 'large'")

class PanelCharacter(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(description="Visual description")
    position: GridPosition = Field(description="Position in 9x9 grid")
    facing: str = Field(description="Facing direction: 'left' or 'right'")
    pose: str = Field(
        description="Physical pose of the character (e.g., 'standing', 'pointing', 'sitting')"
    )
    expression: str = Field(
        description="Facial expression (e.g., 'happy', 'angry', 'surprised')"
    )
    dialogue: str = Field(description="Text for the speech bubble")


class BackgroundLayer(BaseModel):
    type: str = Field(description="Type of background: 'sky', 'indoor', 'space', 'abstract'")
    color: str = Field(description="Base color for the background")
    gradient: Optional[str] = Field(description="Optional gradient specification")

class LandscapeElement(BaseModel):
    type: str = Field(description="Type of element: 'mountain', 'hill', 'sun', 'tree', 'building', 'classroom', 'desk', 'blackboard', etc.")
    position: GridPosition = Field(description="Position in 9x9 grid")
    size: str = Field(description="Size: 'small', 'medium', 'large'")
    details: str = Field(description="Specific details about appearance")

class Panel(BaseModel):
    panel_id: int = Field(description="The panel number")
    concept: str = Field(description="The specific concept explained in this panel")
    background_layer: BackgroundLayer = Field(description="Background layer specification")
    landscape_elements: List[LandscapeElement] = Field(
        default_factory=list,
        description="Landscape elements like mountains, buildings, furniture"
    )
    characters: List[PanelCharacter] = Field(
        description="List of characters in this panel"
    )
    elements: List[PanelElement] = Field(
        default_factory=list,
        description="Additional elements like equations, icons, symbols to render in the panel"
    )


class ConceptGroup(BaseModel):
    concepts: List[str] = Field(description="List of concepts explained in this group")
    panel_range: str = Field(description="Panel range for this group (e.g., '1-5', '6-8')")

class ComicScript(BaseModel):
    panels: List[Panel] = Field(description="Variable number of panels (1-20+ per concept, plus combination panels)")
    concept_groups: List[ConceptGroup] = Field(description="Groups of concepts and their panel ranges")


class AgentState(BaseModel):
    user_prompt: str
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    script: Optional[ComicScript] = None
    assets: Dict[str, str] = Field(
        default_factory=dict
    )  # Map of character name -> PNG path
    html_output: Optional[str] = None
    fast_mode: bool = False


# --- LLM Initialization ---
llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0.7,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

json_llm = ChatOpenAI(
    model=MODEL_NAME,
    temperature=0.5,
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model_kwargs={"response_format": {"type": "json_object"}}
)

# --- Helper Functions ---


def load_guidelines():
    if os.path.exists(GUIDELINES_PATH):
        with open(GUIDELINES_PATH, "r") as f:
            return f.read()
    return ""


def svg_to_png(svg_content: str, output_path: str):
    try:
        cairosvg.svg2png(bytestring=svg_content.encode("utf-8"), write_to=output_path)
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
    Generates the comic script in JSON format with 9x9 grid positioning and element extraction.
    """
    print(f"--- Director Node ({state.run_id}) ---")

    schema_json = json.dumps(ComicScript.model_json_schema(), indent=2)

    prompt_text = f"""
    You are a Comic Director. Generate a comprehensive JSON script for a layered, multi-panel educational comic based on the user's request.

    User Request: "{state.user_prompt}"

    You must output valid JSON that matches the following schema:
    {schema_json}

    LAYERED SCENE RENDERING ORDER:
    1. Background Layer: Sky, indoor space, or abstract background
    2. Landscape Elements: Mountains, hills, sun, trees, buildings, classroom furniture, etc.
    3. Characters: People/figures in the scene
    4. Text & Concept Elements: Dialogue bubbles, equations, icons, symbols

    EDUCATIONAL COMIC STRUCTURE:
    Phase 1 - Individual Concept Panels (1 panel per concept):
    - Break down the topic into fundamental concepts
    - Create EXACTLY 1 panel per concept explaining each idea individually
    - Each panel focuses on one specific concept with appropriate layered background

    Phase 2 - Concept Integration (2-3 concepts per panel):
    - Combine 2-3 related concepts in single panels
    - Show how concepts work together with integrated backgrounds
    - Demonstrate relationships and dependencies

    Phase 3 - Comprehensive Conclusion:
    - Final panels that integrate ALL concepts
    - Provide complete understanding with summary backgrounds
    - Include summary elements and key takeaways

    BACKGROUND LAYER TYPES:
    - sky: Outdoor scenes with weather, time of day
    - indoor: Classrooms, labs, offices, homes
    - space: Stars, planets, cosmic backgrounds
    - abstract: Mathematical, scientific, conceptual backgrounds

    LANDSCAPE ELEMENTS:
    - Natural: mountains, hills, sun, trees, clouds, rivers
    - Urban: buildings, streets, vehicles
    - Educational: classroom, desks, blackboard, books, lab equipment
    - Scientific: atoms, molecules, planets, laboratory tools

    IMPORTANT POSITIONING RULES:
    - Use a 9x9 grid system (coordinates 0-8 for x,y)
    - Position characters and elements to avoid collisions
    - Characters positioned logically (standing on "ground" at y=6-8)
    - Elements positioned in empty grid spaces, avoiding character positions
    - Landscape elements positioned behind characters
    - Text and equations positioned above characters when possible

    ELEMENT EXTRACTION RULES:
    - Look for mathematical equations (e.g., E=mc², F=ma, a²+b²=c²)
    - Extract scientific symbols and icons (e.g., atoms, planets, molecules)
    - Find key textual elements that should be visually emphasized
    - Position elements strategically for educational impact

    Constraints:
    - MAXIMUM 1 panel total for testing
    - Fixed 1-panel structure for testing purposes
    - Max 2 characters per panel
    - 1-3 landscape elements per panel for scene setting
    - Characters reused across panels with unique poses/expressions
    - Use 9x9 grid coordinates for precise positioning
    - Extract and position 1-3 key elements per panel (equations, icons, symbols)
    - Ensure proper layering: Background → Landscape → Characters → Elements
    """

    response = json_llm.invoke(prompt_text)

    try:
        content = response.content
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")

        data = json.loads(content)
        script = ComicScript(**data)

        # Enforce 1 panel maximum limit
        if len(script.panels) > 1:
            print(f"Warning: Generated {len(script.panels)} panels, truncating to 1 maximum.")
            script.panels = script.panels[:1]

        # Post-process to ensure no collisions
        for panel in script.panels:
            occupied_positions = set()
            # Mark character positions as occupied
            for char in panel.characters:
                occupied_positions.add((char.position.x, char.position.y))

            # Adjust element positions to avoid collisions
            for element in panel.elements:
                original_pos = (element.position.x, element.position.y)
                if original_pos in occupied_positions:
                    # Find nearest available position
                    for dx in range(-2, 3):
                        for dy in range(-2, 3):
                            new_x = min(max(element.position.x + dx, 0), 8)
                            new_y = min(max(element.position.y + dy, 0), 8)
                            new_pos = (new_x, new_y)
                            if new_pos not in occupied_positions:
                                element.position.x = new_x
                                element.position.y = new_y
                                occupied_positions.add(new_pos)
                                break
                        else:
                            continue
                        break

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

    # Process every character instance and element in every panel
    guidelines = load_guidelines()
    new_assets = {}

    # Cache for character visual consistency: name -> raw_svg_str
    character_svg_cache = {}

    # Cache for element visual consistency: content -> raw_svg_str
    element_svg_cache = {}

    for p_idx, panel in enumerate(script.panels):
        for c_idx, char in enumerate(panel.characters):
            # Unique ID for this specific instance of the character
            instance_id = f"{p_idx}_{c_idx}"

            print(
                f"Generating asset for: {char.name} (Panel {p_idx}, Position {char.position.x},{char.position.y})"
            )

            # Check if we have a base model for this character
            if char.name in character_svg_cache:
                print(f"   -> Using cached base for {char.name}")
                base_svg = character_svg_cache[char.name]

                if state.fast_mode:
                    print(f"   -> [FAST MODE] Skipping AI modification. Reusing base asset.")
                    svg_code = base_svg
                else:
                    svg_prompt = f"""
                    You have the SVG code for a character named "{char.name}".
                    
                    Current Base SVG:
                    {base_svg}
                    
                    Task: Modify this EXACT SVG code to match a new scene.
                    - New Pose: {char.pose}
                    - New Expression: {char.expression}
                    
                    CRITICAL INSTRUCTIONS:
                    1. KEEP visual identity identical (same colors, same clothes, same features).
                    2. ONLY adjust the paths for limbs and face to match the new pose/expression.
                    3. Output the FULL, valid modified SVG code.
                    4. Do NOT output markdown code blocks, just the XML.
                    """
                    # Only invoke LLM if NOT in fast mode
                    try:
                        response = llm.invoke(svg_prompt)
                        svg_code = response.content.strip()
                    except Exception as e:
                        print(f"Error invoking LLM for modification: {e}")
                        svg_code = base_svg # Fallback to base
            else:
                print(f"   -> Creating new base for {char.name}")
                svg_prompt = f"""
                Generate an SVG for a character named "{char.name}".
                
                Visual Description: {char.visual_desc}
                Pose: {char.pose}
                Expression: {char.expression}
                
                Guidelines:
                {guidelines}
                
                Output ONLY the raw <svg>...</svg> code. No markdown.
                """
                try:
                    response = llm.invoke(svg_prompt)
                    svg_code = response.content.strip()
                except Exception as e:
                    print(f"Error invoking LLM for creation: {e}")
                    svg_code = "" # Handle generic error below

            try:
                # Cleanup code blocks (Common for both paths)
                if "```xml" in svg_code:
                    svg_code = svg_code.replace("```xml", "").replace("```", "")
                if "```svg" in svg_code:
                    svg_code = svg_code.replace("```svg", "").replace("```", "")
                if "```" in svg_code:
                     svg_code = svg_code.replace("```", "")
                     
                svg_code = svg_code.strip()
                
                # Basic validation
                if not svg_code.startswith("<svg") and not svg_code.startswith("<?xml"):
                    print(f"Warning: Output might not be valid SVG for {char.name}")

                # Save to cache if it's the first time
                if char.name not in character_svg_cache and svg_code:
                    character_svg_cache[char.name] = svg_code
        
                # Save SVG File
                char_safe_name = char.name.lower().replace(' ', '_')
                svg_filename = f"{char_safe_name}_p{p_idx}_{c_idx}.svg"
                svg_path = os.path.join(images_dir, svg_filename)
                
                with open(svg_path, "w") as f:
                    f.write(svg_code)
                    
                # Convert to PNG
                png_filename = f"{char_safe_name}_p{p_idx}_{c_idx}.png"
                png_path = os.path.join(images_dir, png_filename)
                
                if svg_to_png(svg_code, png_path):
                    print(f"   -> Saved PNG to {png_path}")
                    new_assets[instance_id] = f"images/{png_filename}"
                else:
                    print(f"   -> Failed to convert {char.name} to PNG.")
                    new_assets[instance_id] = "https://placehold.co/400x800/FF0000/FFFFFF/png?text=Error"
            
            except Exception as e:
                print(f"Error processing {char.name}: {e}")
                new_assets[instance_id] = "https://placehold.co/400x800/FF0000/FFFFFF/png?text=GenError"

        # Process landscape elements (mountains, buildings, furniture, etc.)
        for l_idx, landscape in enumerate(panel.landscape_elements):
            landscape_id = f"landscape_{p_idx}_{l_idx}"

            print(f"Generating landscape element: {landscape.type} (Size: {landscape.size})")

            # Generate SVG for landscape element
            landscape_prompt = f"""
            Generate an SVG representation of a {landscape.size} {landscape.type} for a comic scene.

            Details: {landscape.details}
            Style: Simple, cartoon-like, suitable for background layer
            Requirements:
            - Clean, minimal design
            - Transparent background
            - Appropriate scale for background element
            - Output ONLY the raw <svg>...</svg> code. No markdown.
            """

            try:
                response = llm.invoke(landscape_prompt)
                svg_code = response.content.strip()

                # Cleanup code blocks
                if "```xml" in svg_code:
                    svg_code = svg_code.replace("```xml", "").replace("```", "")
                if "```svg" in svg_code:
                    svg_code = svg_code.replace("```svg", "").replace("```", "")
                if "```" in svg_code:
                    svg_code = svg_code.replace("```", "")

                svg_code = svg_code.strip()

                # Save SVG File
                landscape_safe_name = landscape.type.replace(' ', '_')[:15]
                svg_filename = f"landscape_{landscape_safe_name}_p{p_idx}_{l_idx}.svg"
                svg_path = os.path.join(images_dir, svg_filename)

                with open(svg_path, "w") as f:
                    f.write(svg_code)

                # Convert to PNG
                png_filename = f"landscape_{landscape_safe_name}_p{p_idx}_{l_idx}.png"
                png_path = os.path.join(images_dir, png_filename)

                if svg_to_png(svg_code, png_path):
                    print(f"   -> Saved landscape PNG to {png_path}")
                    new_assets[landscape_id] = f"images/{png_filename}"
                else:
                    print(f"   -> Failed to convert landscape {landscape.type} to PNG.")
                    new_assets[landscape_id] = "https://placehold.co/300x200/CCCCCC/000000/png?text=Landscape"

            except Exception as e:
                print(f"Error processing landscape element {landscape.type}: {e}")
                new_assets[landscape_id] = "https://placehold.co/300x200/CCCCCC/000000/png?text=LandscapeError"

        # Process panel elements (equations, icons, symbols)
        for e_idx, element in enumerate(panel.elements):
            element_id = f"element_{p_idx}_{e_idx}"

            print(f"Generating asset for element: {element.content} (Type: {element.type})")

            # Check if we have a cached version of this element
            if element.content in element_svg_cache:
                print(f"   -> Using cached element: {element.content}")
                svg_code = element_svg_cache[element.content]
            else:
                # Generate SVG for the element
                if element.type == "equation":
                    element_prompt = f"""
                    Generate a clean SVG representation of the mathematical equation: {element.content}

                    Requirements:
                    - Use mathematical notation symbols
                    - Clear, readable typography
                    - Simple, elegant design
                    - Transparent background
                    - Output ONLY the raw <svg>...</svg> code. No markdown.
                    """
                elif element.type == "icon":
                    element_prompt = f"""
                    Generate a simple SVG icon representing: {element.content}

                    Requirements:
                    - Clean, minimal design
                    - Scalable vector graphics
                    - Transparent background
                    - Output ONLY the raw <svg>...</svg> code. No markdown.
                    """
                elif element.type == "symbol":
                    element_prompt = f"""
                    Generate an SVG representation of the symbol/concept: {element.content}

                    Requirements:
                    - Visual representation of the concept
                    - Clear and recognizable
                    - Transparent background
                    - Output ONLY the raw <svg>...</svg> code. No markdown.
                    """
                else:  # text
                    element_prompt = f"""
                    Generate an SVG with the text: {element.content}

                    Requirements:
                    - Clean, readable typography
                    - Appropriate font styling
                    - Transparent background
                    - Output ONLY the raw <svg>...</svg> code. No markdown.
                    """

                try:
                    response = llm.invoke(element_prompt)
                    svg_code = response.content.strip()
                except Exception as e:
                    print(f"Error generating SVG for element {element.content}: {e}")
                    svg_code = f'<svg width="100" height="50" xmlns="http://www.w3.org/2000/svg"><text x="10" y="30" font-family="Arial" font-size="16">{element.content}</text></svg>'  # Fallback

            try:
                # Cleanup code blocks
                if "```xml" in svg_code:
                    svg_code = svg_code.replace("```xml", "").replace("```", "")
                if "```svg" in svg_code:
                    svg_code = svg_code.replace("```svg", "").replace("```", "")
                if "```" in svg_code:
                    svg_code = svg_code.replace("```", "")

                svg_code = svg_code.strip()

                # Cache the element
                if element.content not in element_svg_cache:
                    element_svg_cache[element.content] = svg_code

                # Save SVG File
                element_safe_name = element.content.replace(' ', '_').replace('=', 'eq').replace('²', '2')[:20]  # Safe filename
                svg_filename = f"element_{element_safe_name}_p{p_idx}_{e_idx}.svg"
                svg_path = os.path.join(images_dir, svg_filename)

                with open(svg_path, "w") as f:
                    f.write(svg_code)

                # Convert to PNG
                png_filename = f"element_{element_safe_name}_p{p_idx}_{e_idx}.png"
                png_path = os.path.join(images_dir, png_filename)

                if svg_to_png(svg_code, png_path):
                    print(f"   -> Saved element PNG to {png_path}")
                    new_assets[element_id] = f"images/{png_filename}"
                else:
                    print(f"   -> Failed to convert element {element.content} to PNG.")
                    new_assets[element_id] = "https://placehold.co/200x100/FF0000/FFFFFF/png?text=ElementError"

            except Exception as e:
                print(f"Error processing element {element.content}: {e}")
                new_assets[element_id] = "https://placehold.co/200x100/FF0000/FFFFFF/png?text=ElementError"

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
            "concept": panel.concept,
            "background_layer": panel.background_layer.model_dump(),
            "characters": [],
            "landscape_elements": [],
            "elements": []
        }

        # Add landscape elements
        for l_idx, landscape in enumerate(panel.landscape_elements):
            landscape_id = f"landscape_{p_idx}_{l_idx}"
            landscape_obj = {
                "type": landscape.type,
                "image": assets.get(landscape_id, ""),
                "position": landscape.position.model_dump(),
                "size": landscape.size,
                "details": landscape.details,
            }
            panel_obj["landscape_elements"].append(landscape_obj)

        # Add characters
        for c_idx, char in enumerate(panel.characters):
            instance_id = f"{p_idx}_{c_idx}"
            char_obj = {
                "name": char.name,
                "image": assets.get(instance_id, ""),  # Use instance ID
                "position": char.position.model_dump(),  # Grid position
                "facing": char.facing,
                "dialogue": wrap_text(char.dialogue),
                "pose": char.pose,
                "expression": char.expression,
            }
            panel_obj["characters"].append(char_obj)

        # Add elements to panel data
        for e_idx, element in enumerate(panel.elements):
            element_id = f"element_{p_idx}_{e_idx}"
            element_obj = {
                "type": element.type,
                "content": element.content,
                "image": assets.get(element_id, ""),
                "position": element.position.model_dump(),  # Grid position
                "size": element.size,
            }
            panel_obj["elements"].append(element_obj)

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
    script = cast(ComicScript, result["script"])
    with open(os.path.join(run_dir, "script.json"), "w") as f:
        f.write(script.model_dump_json(indent=4))

    print(f"Comic generated! Open {output_filename} to view.")
