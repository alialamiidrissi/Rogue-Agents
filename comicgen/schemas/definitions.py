from typing import List, Dict, Optional
import uuid
from pydantic import BaseModel, Field

class Character(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(
        description="Visual description of the character (e.g., stick figure details)"
    )


class BackgroundLayer(BaseModel):
    type: str = Field(description="Background type: 'sky', 'indoor', 'space', 'abstract'")
    color: str = Field(description="CSS color name or hex code")
    gradient: Optional[str] = Field(default=None, description="Optional CSS gradient")


class PanelCharacter(BaseModel):
    name: str = Field(description="Name of the character")
    visual_desc: str = Field(description="Visual description")
    slot: str = Field(description="Position in the panel: 'left' or 'right'")
    facing: str = Field(description="Facing direction: 'left' or 'right'")
    pose: str = Field(
        description="Physical pose of the character (e.g., 'standing', 'pointing', 'sitting')"
    )
    expression: str = Field(
        description="Facial expression (e.g., 'happy', 'angry', 'surprised')"
    )
    dialogue: str = Field(description="Text for the speech bubble")


class Panel(BaseModel):
    panel_id: int = Field(description="The panel number")
    concept: str = Field(description="The specific concept explained in this panel")
    # background_layer: BackgroundLayer = Field(description="Background layer specification")
    characters: List[PanelCharacter] = Field(
        description="List of characters in this panel"
    )


class ComicScript(BaseModel):
    panels: List[Panel] = Field(description="List of 3 panels for the comic")


class AgentState(BaseModel):
    user_prompt: str
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    script: Optional[ComicScript] = None
    assets: Dict[str, str] = Field(
        default_factory=dict
    )  # Map of character name -> PNG path
    html_output: Optional[str] = None
    fast_mode: bool = False
