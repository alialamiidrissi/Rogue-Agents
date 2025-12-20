
import os
import json
from jinja2 import Environment, FileSystemLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from comicgen.schemas.comicgen import ComicCharacter
from comicgen.schemas.definitions import AgentState, ComicScript
from comicgen.utils import add_retry, fetch_comicgen_asset, wrap_text
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
# Re-using configs or passing them in would be better, but for now hardcode or use envs
MODEL_NAME = "gemini-2.5-flash"
BASE_OUTPUT_DIR = "./runs" 

# Initialize generic LLMs
llm = ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=0.7)
json_llm = ChatGoogleGenerativeAI(
    model=MODEL_NAME, temperature=0.5, response_format={"type": "json_object"}
).with_retry(exponential_jitter_params={"initial": 3})

# --- Nodes ---

def single_page_director_node(state: AgentState):
    """
    Generates the comic script in JSON format (Original 3-panel version).
    """
    print(f"--- Director Node ({state.run_id}) ---")

    prompt_text = f"""
    You are a Comic Director. Generate a script for a 3-panel comic based on the user's request.

    User Request: "{state.user_prompt}"

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


def story_director_node(state: AgentState):
    """
    Generates a multi-page comic script in JSON format (Multiples of 3 panels).
    """
    print(f"--- Story Director Node ({state.run_id}) ---")

    # FAST MODE CHECK
    if state.fast_mode and state.script:
        print("🚀 Fast Mode: Reusing existing script.")
        return {"script": state.script}

    prompt_text = f"""
    You are a Comic Director. Generate a script for a graphic novel style comic based on the user's request.
    
    User Request: "{state.user_prompt}"
    
    The story should be long enough to be interesting. 
    Ideally 6 to 9 panels (2 or 3 pages).
    IMPORTANT: The total number of panels MUST be a multiple of 3 (e.g. 3, 6, 9, 12).
    
    Structure:
    - Each page has exactly 3 panels (2 top, 1 bottom).
    - Plan your pacing so that every 3rd panel completes a "page" or scene beat.
    
    Constraints:
    - Max 2 characters per panel.
    - Reuse characters (names/descriptions) across panels for consistency.
    - Vary poses and expressions.
    
    Available Characters:
    1. "Aavatar": Customizable human.
    2. "Ethan": Man with beard & glasses.
    3. "Bean": Living coffee mug.
    4. "Deenuova" / "Deynuovo": Specific humans.
    5. "Bill" / "Sophie": Front-view only.
    """

    structured_llm = add_retry(llm.with_structured_output(ComicScript.model_json_schema(), method="json_schema"))
    try:
        response = structured_llm.invoke(prompt_text)
        if isinstance(response, dict):
            script = ComicScript(**response)
        else:
            script = response
            
        # Validate panel count
        count = len(script.panels)
        print(f"Director generated {count} panels.")
        if count % 3 != 0:
            print(f"Warning: Panel count {count} is not divisible by 3. Story compositor handles this, but pacing might be off.")
            
    except Exception as e:
        print(f"Error parsing JSON from Director: {e}")
        script = ComicScript(panels=[])

    return {"script": script}


def asset_generator_node(state: AgentState):
    """
    Generates SVGs, converts them to PNGs, and stores paths.
    Uses caching from state.assets to avoid re-generating identical descriptions if needed,
    but primarily focuses on consistency prompts.
    """
    print(f"--- Asset Generator Node ({state.run_id}) ---")

    if not state.script:
        print("No script found.")
        return {"assets": state.assets}

    # FAST MODE CHECK
    if state.fast_mode and state.assets:
        print("🚀 Fast Mode: Reusing existing assets.")
        return {"assets": state.assets}

    # Setup Run Directories
    run_dir = os.path.join(BASE_OUTPUT_DIR, state.run_id)
    images_dir = os.path.join(run_dir, "images")
    params_dir = os.path.join(run_dir, "params")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(params_dir, exist_ok=True)

    script = state.script
    existing_assets = state.assets.copy() # Avoid mutating original directly till return
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
            # Unique ID for this specific instance in this specific panel
            instance_id = f"{p_idx}_{c_idx}"

            print(f"Generating asset for: {char.name} (Panel {p_idx}, Slot {char.slot})")
            
            schema_json = json.dumps(ComicCharacter.model_json_schema(), indent=2)

            # Track character styles for consistency across panels
            if 'character_styles' not in locals():
                character_styles = {}

            prev_style_info = ""
            if char.name in character_styles:
                prev_style_info = f"PREVIOUS STYLE FOR {char.name}: {json.dumps(character_styles[char.name])}\nUse the same character, hair, and clothing attributes for consistency."

            # Construct Prompt
            prompt = f"""
            {consistency_context}
            
            Target Character: "{char.name}"
            Visual Description: "{char.visual_desc}"
            
            {prev_style_info}

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
                    if isinstance(content, list):
                        content = content[0]["text"]
                    print(f"   -> Generated JSON: {content}")
                    data = json.loads(content)

                    # Save parameters for caching/debugging
                    params_file = os.path.join(params_dir, f"{instance_id}.json")
                    with open(params_file, "w") as pf:
                        json.dump(data, pf, indent=2)

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
                     # Store relative path for HTML
                     new_assets[instance_id] = f"images/{png_filename}"
                else:
                    new_assets[instance_id] = "https://placehold.co/400x800/FF0000/FFFFFF/png?text=FetchError"
            else:
                 new_assets[instance_id] = "https://placehold.co/400x800/FF0000/FFFFFF/png?text=ConfigError"

    updated_assets = {**existing_assets, **new_assets}
    return {"assets": updated_assets}


def compositor_node(state: AgentState):
    """
    Renders the Single Page HTML using Jinja2 template.
    """
    print(f"--- Compositor Node ({state.run_id}) ---")
    if not state.script:
        return {"html_output": "Error: No script generated."}

    script = state.script
    assets = state.assets
    
    TEMPLATE_DIR = "comicgen/templates"
    TEMPLATE_NAME = "template_panels.html"

    llm_with_retry = add_retry(llm)

    # Generate title and subtitle
    try:
        title_prompt = f"""
        Create a fun cartoon title and subtitle for a comic explaining: "{state.user_prompt}"

        Title: Should be catchy and cartoon-like.
        Subtitle: Explain the main characters.

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
                char_data["dialogue"] = wrap_text(char_data["dialogue"], width=20)

        panels_data.append(panel_data)

    # Render Template
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    try:
        template = env.get_template(TEMPLATE_NAME)
        html_content = template.render(panels=panels_data, comic_title=title, comic_subtitle=subtitle)
        return {"html_output": html_content}
    except Exception as e:
        return {"html_output": f"Error rendering template: {e}"}

def story_compositor_node(state: AgentState):
    """
    Renders multiple HTML pages (Index + Page 1..N).
    Each page contains 3 panels.
    Returns the path to the index.html as the primary output, but writes all files to disk.
    """
    print(f"--- Story Compositor Node ({state.run_id}) ---")
    if not state.script:
        return {"html_output": "Error: No script generated."}

    script = state.script
    assets = state.assets
    run_dir = os.path.join(BASE_OUTPUT_DIR, state.run_id)
    os.makedirs(run_dir, exist_ok=True)
    
    TEMPLATE_DIR = "comicgen/templates"
    ENV = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    
    # 1. Generate Metadata (Title/Subtitle)
    llm_with_retry = add_retry(llm)
    try:
        title_prompt = f"""
        Create a fun cartoon title and subtitle for a comic story: "{state.user_prompt}"
        Title: Catchy.
        Subtitle: Brief summary.
        Output format:
        Title: [title]
        Subtitle: [subtitle]
        """
        title_response = llm_with_retry.invoke(title_prompt)
        text = title_response.content.strip()
        title = "Amazing Story"
        subtitle = "A visual adventure."
        for line in text.split('\n'):
            if line.startswith('Title:'): title = line.replace('Title:', '').strip()
            elif line.startswith('Subtitle:'): subtitle = line.replace('Subtitle:', '').strip()
    except:
        title = "Amazing Story"
        subtitle = "A visual adventure."

    # 2. Process Panels & Chunking
    all_panels_processed = []
    for p_idx, panel in enumerate(script.panels):
        p_data = panel.model_dump()
        for c_idx, char in enumerate(p_data["characters"]):
            instance_id = f"{p_idx}_{c_idx}"
            char["image"] = assets.get(instance_id, "")
            if "dialogue" in char:
                char["dialogue"] = wrap_text(char["dialogue"], width=20)
        all_panels_processed.append(p_data)

    # Chunk into groups of 3
    chunk_size = 3
    pages = [all_panels_processed[i:i + chunk_size] for i in range(0, len(all_panels_processed), chunk_size)]
    total_pages = len(pages)
    
    # 3. Render Pages
    try:
        page_template = ENV.get_template("template_story_page.html")
    except:
        # Fallback if template doesn't exist yet (during dev)
        print("Warning: template_story_page.html not found.")
        return {"html_output": "Error: Missing template."}

    for i, page_panels in enumerate(pages):
        page_num = i + 1
        prev_link = f"page_{page_num - 1}.html" if page_num > 1 else "index.html"
        next_link = f"page_{page_num + 1}.html" if page_num < total_pages else None
        
        html = page_template.render(
            panels=page_panels,
            comic_title=title,
            page_num=page_num,
            total_pages=total_pages,
            prev_link=prev_link,
            next_link=next_link,
            index_link="index.html"
        )
        
        with open(os.path.join(run_dir, f"page_{page_num}.html"), "w") as f:
            f.write(html)
            
    # 4. Render Index
    try:
        index_template = ENV.get_template("template_index.html")
        index_html = index_template.render(
            comic_title=title,
            comic_subtitle=subtitle,
            total_pages=total_pages,
            start_link="page_1.html",
            pages=[{'num': i+1, 'link': f'page_{i+1}.html'} for i in range(total_pages)]
        )
        # Writes index.html to disk - this is what main_comicgen expects to read back if we were returning one string
        # But we really want to just point to it.
        # For compatibility with AgentState.html_output, we can return the index html.
        return {"html_output": index_html}
        
    except Exception as e:
        print(f"Error rendering index: {e}")
        return {"html_output": f"Error rendering index: {e}"}
