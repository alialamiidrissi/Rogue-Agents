
from typing import Literal, Union
from pydantic import BaseModel, Field
from urllib.parse import urlencode

# ==========================================
# 1. SHARED / GLOBAL SETTINGS
# ==========================================

class GlobalVisuals(BaseModel):
    mirror: bool = Field(False, description="Flip the image horizontally.")
    box: Literal["", "box", "circle", "outline"] = Field("", description="Background shape.")
    boxcolor: str = Field("#000000", description="Background color hex code.")

# ==========================================
# 2. COMPLEX CHARACTER: AAVATAR
# ==========================================

# --- Aavatar Sub-components ---

# 1. Gender / Hairstyle Dependencies
class AavatarFemale(BaseModel):
    gender: Literal["female"] = "female"
    hairstyle: Literal["bindi", "blondecurly", "blondeshort", "densehair", "densehairwithband", "hairband", "highbun", "messyponytail", "oldladywithglasses", "shorthair", "wavy"]

class AavatarMale(BaseModel):
    gender: Literal["male"] = "male"
    hairstyle: Literal["brettbeard", "egyptiangoatee", "englishmoustache", "fullgoatee", "oldman", "oldmanwithglasses", "paintersmoustache", "smallgoatee", "spikes"]

class AavatarUnisex(BaseModel):
    gender: Literal["unisex"] = "unisex"
    hairstyle: Literal["bald", "densedreads", "mediumdreads", "mediumhair", "mediumhairwithglasses", "topknotbun", "turban"]

# 2. Expression
AavatarEmotion = Literal["afraid", "angry", "annoyed", "blush", "confused", "cry", "cryingloudly", "cunning", "curious", "disappointed", "dozing", "drunk", "excited", "happy", "hearteyes", "irritated", "lookingdown", "lookingleft", "lookingright", "lookingup", "mask", "neutral", "nevermind", "ooh", "rofl", "rollingeyes", "sad", "scared", "shocked", "shout", "smile", "smirk", "starstruck", "surprised", "tired", "tongueout", "whistle", "wink", "worried"]

class AavatarExpression(BaseModel):
    style: Literal["sketchy", "strokes", "thinlines"]
    emotion: AavatarEmotion

# 3. Attire / Pose Dependencies
class AavatarPoseBodycon(BaseModel):
    attire: Literal["bodycon"] = "bodycon"
    pose: Literal["handonhip", "handsfolded", "handsonhip", "holdingbag", "holdinglaptop", "pointingleft", "shy", "sittingonbeanbag", "super", "walk", "wonderwoman"]

class AavatarPoseCasualFullSleeveTee(BaseModel):
    attire: Literal["casualfullsleevetee"] = "casualfullsleevetee"
    pose: Literal["angry", "handsfolded", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointingright", "pointingup", "readingpaper", "ridingbicycle", "ridingbike", "shrug", "sittingatdesk", "sittingatdeskhandsspread", "sittingatdeskholdingmobile", "sittingonbeanbagholdinglaptop", "sittingonbeanbagholdingmobile", "sittingonfloorexplaining", "sittingonfloorholdinglaptop", "sittingonfloorshrug", "super", "thinking", "thumbsup", "yuhoo"]

class AavatarPoseCasualTee(BaseModel):
    attire: Literal["casualtee"] = "casualtee"
    pose: Literal["angry", "handsfolded", "handsheldback", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointing45degree", "pointingright", "pointingup", "readingpaper", "ridingbicycle", "ridingbike", "shrug", "sittingatdesk", "sittingatdeskhandsspread", "sittingatdeskholdingmobile", "sittingonbeanbagholdinglaptop", "sittingonbeanbagholdingmobile", "sittingonthefloorexplaining", "sittingonthefloorholdinglaptop", "sittingonthefloorshrug", "super", "thinking", "thumbsup", "yuhoo"]

class AavatarPoseFormal(BaseModel):
    attire: Literal["formal"] = "formal"
    pose: Literal["explaining", "explaining45degreesdown", "explaining45degreesup", "explainingwithbothhands", "handsclasped", "handstouchingchin", "holdingboard", "holdingbook", "holdingstick", "normal", "pointingleft"]

class AavatarPoseFormalSuit(BaseModel):
    attire: Literal["formalsuit"] = "formalsuit"
    pose: Literal["handsfolded", "handsheldback", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointing45degree", "pointingright", "pointingup", "readingpaper", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class AavatarPoseFullSleeveShirt(BaseModel):
    attire: Literal["fullsleeveshirt"] = "fullsleeveshirt"
    pose: Literal["angry", "handsfolded", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointingright", "pointingup", "readingpaper", "ridingbicycle", "ridingbike", "run", "shrug", "sittingatdesk", "sittingatdeskhandsspread", "sittingatdeskholdingmobile", "sittingonbeanbagexplaining", "sittingonbeanbagholdinglaptop", "sittingonfloorexplaining", "sittingonfloorholdinglaptop", "sittingonthefloorshrug", "super", "thinking", "thumbsup", "yuhoo"]

class AavatarPoseSaree(BaseModel):
    attire: Literal["saree"] = "saree"
    pose: Literal["angry", "explaining", "handsfolded", "handsonhip", "hi", "holdingcoffee", "normal", "pointingup", "readingpaper", "shrug", "super", "thumbsup"]

class AavatarPoseStickFigure(BaseModel):
    attire: Literal["stickfigure"] = "stickfigure"
    pose: Literal["angry", "handsfolded", "handsheldback", "handsonhip", "holdingbook", "holdinglaptop", "pointingright", "pointingup", "readingpaper", "super", "thinking", "thumbsup", "yuhoo"]

class AavatarPoseTuckedInShirt(BaseModel):
    attire: Literal["tuckedinshirt"] = "tuckedinshirt"
    pose: Literal["dance", "handsclasped", "handsfolded", "handsinpocket", "handsonhead", "handsonhip", "holdingbag", "leaning", "superman"]

class AavatarPoseUniform(BaseModel):
    attire: Literal["uniform"] = "uniform"
    pose: Literal["angry", "handsfolded", "handsheldback", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointingleft", "pointingright", "pointingup", "readingpaper", "ridingbicycle", "ridingbike", "shrug", "sittingatdesk", "sittingonbeanbagholdinglaptop", "sittingonbeanbagholdingmobile", "sittingonfloorexplaining", "sittingonfloorholdinglaptop", "sittingonfloorshrug", "super", "thinking", "thumbsup", "yuhoo"]

# --- Main Aavatar Class ---

class Aavatar(BaseModel):
    character: Literal["aavatar"] = "aavatar"
    description: str = Field("Generic customizable avatar.", frozen=True)
    
    # 1. Head (Gender -> Hairstyle)
    head: Union[AavatarFemale, AavatarMale, AavatarUnisex] = Field(..., description="Gender and hairstyle configuration.")

    # 2. Face (Style -> Emotion)
    face: AavatarExpression = Field(..., description="Face style and emotion.")

    # 3. Body (Attire -> Pose)
    body: Union[
        AavatarPoseBodycon, 
        AavatarPoseCasualFullSleeveTee, 
        AavatarPoseCasualTee, 
        AavatarPoseFormal, 
        AavatarPoseFormalSuit, 
        AavatarPoseFullSleeveShirt, 
        AavatarPoseSaree, 
        AavatarPoseStickFigure, 
        AavatarPoseTuckedInShirt, 
        AavatarPoseUniform
    ] = Field(..., description="Attire and pose configuration.")

# ==========================================
# 3. COMPOSITIONAL: HUMAAANS
# ==========================================

# --- Humaaans ---
class HumaaansHead(BaseModel):
    # Pattern: head/front/{{head}}
    head: Literal["afro", "airy", "caesar", "chongo", "curly", "hijab-1", "hijab2", "long", "no-hair", "pony", "rad", "short-1", "short-2", "short-beard", "top", "turban-1", "turban2", "wavy"]

class HumaaansBody(BaseModel):
    # Pattern: body/{{body}}
    body: Literal["hoodie", "jacket-2", "jacket", "lab-coat", "long-sleeve", "pointing-forward", "pointing-up", "pregnant", "trench-coat", "turtle-neck"]

class HumaaansBottomSitting(BaseModel):
    # Pattern: bottom/sitting/{{bottom}}
    pose_type: Literal["sitting"] = "sitting"
    bottom: Literal["baggy-pants", "skinny-jeans-1", "sweat-pants", "wheelchair"]

class HumaaansBottomStanding(BaseModel):
    # Pattern: bottom/standing/{{bottom}}
    pose_type: Literal["standing"] = "standing"
    bottom: Literal["baggy-pants", "jogging", "shorts", "skinny-jeans-walk", "skinny-jeans", "skirt", "sprint", "sweatpants"]

class Humaaans(BaseModel):
    character: Literal["humaaans"] = "humaaans"
    description: str = Field("Artistic flat style people.", frozen=True)
    head_config: HumaaansHead
    body_config: HumaaansBody
    bottom_config: Union[HumaaansBottomSitting, HumaaansBottomStanding]

# ==========================================
# 4. ANGLE-DEPENDENT CHARACTERS
# (Bean, Deenuova, Deynuovo, Ethan, Priyanuova, Ringonuovo)
# ==========================================

# --- Ethan (Complex) ---
# --- Ethan (Complex) ---
class EthanBack(BaseModel):
    angle: Literal["back"] = "back"
    emotion: Literal["backsidehead"]
    pose: Literal["handpointingup", "handsfolded", "handsonhip", "normal"]

class EthanSide(BaseModel):
    angle: Literal["side"] = "side"
    emotion: Literal["afraid", "angry", "cry", "cryingloudly", "curious", "excited", "happy", "irritated", "lookingdown", "lookingup", "neutral", "ooh", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "wink"]
    pose: Literal["explaining45degrees", "holdingstick", "normal", "pointingatboard", "pointingright", "pointingrightat45degrees", "righthandpointing"]

class EthanStraight(BaseModel):
    angle: Literal["straight"] = "straight"
    emotion: Literal["afraid", "angry", "annoyed", "cry", "cryingloudly", "cunning", "curious", "excited", "happy", "irritated", "lookingdown", "lookingleft", "lookingright", "lookingup", "neutral", "ooh", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "wink"]
    pose: Literal["explaining", "explaining45degreesdown", "explaining45degreesup", "explainingwithbothhands", "handsclasped", "handstouchingchin", "holdingboard", "holdingbook", "holdingstick", "normal", "pointingleft"]

class Ethan(BaseModel):
    character: Literal["ethan"] = "ethan"
    description: str = Field("Man with beard & glasses.", frozen=True)
    properties: Union[EthanBack, EthanSide, EthanStraight]

# --- Bean ---
# --- Bean ---
class BeanSide(BaseModel):
    angle: Literal["side"] = "side"
    emotion: Literal["angry", "annoyed", "blush", "cry", "curious", "hmm", "lookingdown", "lookingup", "neutral", "sad", "shocked", "shout", "smile", "tired", "wink", "worried", "yuhoo"]
    pose: Literal["angry", "handsfolded", "handsonhip", "holdingbook", "holdinglaptop", "pointingright", "pointingup", "readingpaper", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class BeanStraight(BaseModel):
    angle: Literal["straight"] = "straight"
    emotion: Literal["angry", "annoyed", "blush", "cry", "curious", "hmm", "lookingdown", "lookingup", "neutral", "sad", "shout", "smile", "tired", "wink", "worried", "yuhoo"]
    pose: Literal["angry", "handsfolded", "handsonhip", "holdingbook", "holdinglaptop", "pointingright", "pointingup", "readingpaper", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class Bean(BaseModel):
    character: Literal["bean"] = "bean"
    description: str = Field("A coffee mug character.", frozen=True)
    properties: Union[BeanSide, BeanStraight]

# --- Deenuova (Female + Glasses) ---
# --- Deenuova (Female + Glasses) ---
class DeenuovaSide(BaseModel):
    angle: Literal["side"] = "side"
    emotion: Literal["afraid", "angry", "confused", "cry", "cunning", "curious", "dozing", "excited", "happy", "hmm", "irritated", "laugh", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["explaining", "handsfolded", "handsinpocket", "holdingcoffee", "holdinglaptop", "holdingmobile", "pointingright", "pointingup", "readingpaper", "rightturn", "shrug"]

class DeenuovaSitting(BaseModel):
    angle: Literal["sitting"] = "sitting"
    emotion: Literal["afraid", "angry", "confused", "cry", "cunning", "curious", "dozing", "excited", "happy", "hmm", "irritated", "laugh", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["ridingbicycle", "ridingbike", "sittingatdesk", "sittingatdeskhandsspread", "sittingatdeskholdingmobile", "sittingonbeanbagholdinglaptop", "sittingonbeanbagholdingmobile", "sittingonthefloorexplaining", "sittingonthefloorholdinglaptop", "sittingonthefloorshrug"]

class DeenuovaStraight(BaseModel):
    angle: Literal["straight"] = "straight"
    emotion: Literal["afraid", "angry", "annoyed", "confused", "cry", "cryingloudly", "cunning", "curious", "dozing", "excited", "hmm", "irritated", "laugh", "lookingdown", "lookingleft", "lookingright", "lookingup", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["handsfolded", "handsheldback", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointing45degree", "pointingright", "pointingup", "readingpaper", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class Deenuova(BaseModel):
    character: Literal["deenuova"] = "deenuova"
    description: str = Field("Female with glasses and curly hair.", frozen=True)
    properties: Union[DeenuovaSide, DeenuovaSitting, DeenuovaStraight]

# --- Deynuovo (Male + Long Hair) ---
# --- Deynuovo (Male + Long Hair) ---
class DeynuovoSide(BaseModel):
    angle: Literal["side"] = "side"
    emotion: Literal["afraid", "angry", "cryingloudly", "curious", "dozing", "excited", "hmm", "laugh", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["handsfolded", "handsinpocket", "holdingcoffee", "holdingmobile", "leftturn", "leftturnhandsfolded", "pointingright", "pointingup", "readingpaper", "thumbsup", "yuhoo"]

class DeynuovoSitting(BaseModel):
    angle: Literal["sitting"] = "sitting"
    emotion: Literal["afraid", "angry", "cryingloudly", "curious", "dozing", "hmm", "laugh", "lookingdown", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["ridingbicycle", "ridingbike", "sittingatdesk", "sittingatdeskhandsspread", "sittingatdeskholdingmobile", "sittingonbeanbagholdinglaptop", "sittingonbeanbagholdingmobile", "sittingonfloorexplaining", "sittingonfloorholdinglaptop", "sittingonfloorshrug"]

class DeynuovoStraight(BaseModel):
    angle: Literal["straight"] = "straight"
    emotion: Literal["afraid", "angry", "confused", "cryingloudly", "cunning", "curious", "dozing", "excited", "hmm", "irritated", "laugh", "lookingdown", "lookingright", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["angry", "handsfolded", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointingright", "pointingup", "readingpaper", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class Deynuovo(BaseModel):
    character: Literal["deynuovo"] = "deynuovo"
    description: str = Field("Male with long hair and beard.", frozen=True)
    properties: Union[DeynuovoSide, DeynuovoSitting, DeynuovoStraight]

# --- Priyanuova (Sitting/Straight only) ---
# --- Priyanuova (Sitting/Straight only) ---
class PriyanuovaSitting(BaseModel):
    angle: Literal["sitting"] = "sitting"
    emotion: Literal["afraid", "angry", "annoyed", "blush", "cry", "cryingloudly", "cunning", "curious", "dozing", "excited", "happy", "hmm", "irritated", "laugh", "lookingdown", "lookingleft", "lookingright", "lookingup", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["ridingbicycle", "ridingbike", "ridingcar", "sittingatdesk", "sittingonbeanbagholdinglaptop", "sittingonbeanbagholdingmobile", "sittingonthefloorexplaining", "sittingonthefloorholdinglaptop", "sittingonthefloorshrug"]

class PriyanuovaStraight(BaseModel):
    angle: Literal["straight"] = "straight"
    emotion: Literal["afraid", "angry", "annoyed", "blush", "cry", "cunning", "curious", "excited", "happy", "irritated", "laugh", "lookingdown", "lookingleft", "lookingright", "lookingup", "loudcry", "neutral", "rofl", "rollingeyes", "sad", "shocked", "shout", "sleep", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["angry", "handsfolded", "handsheldback", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointingleft", "pointingright", "pointingup", "readingpaper", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class Priyanuova(BaseModel):
    character: Literal["priyanuova"] = "priyanuova"
    description: str = Field("Female comic style.", frozen=True)
    properties: Union[PriyanuovaSitting, PriyanuovaStraight]

# --- Ringonuovo (Sitting/Straight only) ---
# --- Ringonuovo (Sitting/Straight only) ---
class RingonuovoSitting(BaseModel):
    angle: Literal["sitting"] = "sitting"
    emotion: Literal["angry", "confused", "cry", "cunning", "curious", "dozing", "excited", "happy", "hmm", "irritated", "laugh", "lookingdown", "lookingleft", "lookingright", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["ridingbicycle", "ridingbike", "ridingcar", "sittingatdesk", "sittingatdeskhandsspread", "sittingatdeskholdingmobile", "sittingonbeanbagexplaining", "sittingonbeanbagholdinglaptop", "sittingonfloorexplaining", "sittingonfloorholdinglaptop", "sittingonthefloorshrug"]

class RingonuovoStraight(BaseModel):
    angle: Literal["straight"] = "straight"
    emotion: Literal["angry", "confused", "cry", "cunning", "curious", "dozing", "excited", "happy", "hmm", "irritated", "laugh", "lookingdown", "lookingleft", "lookingright", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
    pose: Literal["angry", "handsfolded", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointingright", "pointingup", "readingpaper", "run", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class Ringonuovo(BaseModel):
    character: Literal["ringonuovo"] = "ringonuovo"
    description: str = Field("Male comic style.", frozen=True)
    properties: Union[RingonuovoSitting, RingonuovoStraight]

# ==========================================
# 5. FLAT CHARACTERS (NO ANGLE)
# (Bill, Sophie, Aryan*) 
# *Note: Aryan was in your JSON as having patterns ["emotion", "pose"] only, no angle.
# ==========================================

# --- Bill & Sophie (No Angle) ---
BillEmotion = Literal["afraid", "angry", "confused", "cry", "cunning", "curious", "dozing", "excited", "happy", "hmm", "irritated", "laugh", "neutral", "ooh", "rofl", "rollingeyes", "sad", "shocked", "shout", "smile", "smirk", "surprised", "tired", "wink", "worried"]
BillPose = Literal["handsfolded", "handsheldback", "handsinpocket", "handsonhip", "holdingbook", "holdingcoffee", "holdinglaptop", "holdingmobile", "holdingumbrella", "pointing45degree", "pointingright", "pointingup", "readingpaper", "shrug", "super", "thinking", "thumbsup", "yuhoo"]

class Bill(BaseModel):
    character: Literal["bill"] = "bill"
    description: str = Field("Man in a suit.", frozen=True)
    emotion: BillEmotion
    pose: BillPose

SophieEmotion = BillEmotion # Same list as Bill
SophiePose = BillPose # Same list as Bill

class Sophie(BaseModel):
    character: Literal["sophie"] = "sophie"
    description: str = Field("Grandma character.", frozen=True)
    emotion: SophieEmotion
    pose: SophiePose

# --- Aryan ---
AryanEmotion = Literal["angry", "blush", "confused", "cry", "hmm", "laugh", "loudcry", "sad", "shocked", "smile", "wink", "worried"]
AryanPose = Literal["handsfolded", "handsinpocket"]

class Aryan(BaseModel):
    character: Literal["aryan"] = "aryan"
    description: str = Field("A customizable Male comic-style avatar", frozen=True)
    emotion: AryanEmotion
    pose: AryanPose

# ==========================================
# MASTER SCHEMA
# ==========================================

class ComicCharacter(BaseModel):
    visuals: GlobalVisuals = Field(default_factory=GlobalVisuals)    
    # Complete Union of ALL characters
    character_data: Union[
        Aavatar, 
        # Humaaans, 
        Ethan, 
        Bean, 
        Deenuova, 
        Deynuovo, 
        Priyanuova, 
        Ringonuovo,
        Bill, 
        Sophie,
        Aryan
    ]

    def to_url(self) -> str:
        base_url = "https://gramener.com/comicgen/v1/comic"
        data = self.character_data
        
        # 1. Global params
        params = {
            "name": data.character,
            "mirror": "mirror" if self.visuals.mirror else "",
            "box": self.visuals.box,
            "boxcolor": self.visuals.boxcolor
        }

        # 2. Logic for 'Aavatar'
        if data.character == "aavatar":
            params.update({
                "gender": data.head.gender,
                "character": data.head.hairstyle,
                "facestyle": data.face.style,
                "emotion": data.face.emotion,
                "attire": data.body.attire,
                "pose": data.body.pose
            })

        # 3. Logic for 'Humaaans'
        elif data.character == "humaaans":
            params.update({
                "head": data.head_config.head,
                "body": data.body_config.body,
                "bottom": data.bottom_config.bottom
            })
        
        # 4. Logic for Nested Property Models (Ethan, Bean, Deenuova, Deynuovo, Priyanuova, Ringonuovo)
        elif data.character in ["ethan", "bean", "deenuova", "deynuovo", "priyanuova", "ringonuovo"]:
             params.update({
                "angle": data.properties.angle,
                "emotion": data.properties.emotion,
                "pose": data.properties.pose
            })

        # 5. Logic for Standard Characters (Bill, Sophie, Aryan)
        else:
            # Angle does not exist for these
            params["emotion"] = data.emotion
            params["pose"] = data.pose

        # Clean empty values
        query_string = urlencode({k: v for k, v in params.items() if v})
        # Clean empty values
        query_string = urlencode({k: v for k, v in params.items() if v})
        return f"{base_url}?{query_string}&ext=png"

