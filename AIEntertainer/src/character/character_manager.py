import yaml
import json
import requests
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import random


@dataclass
class Character:
    name: str
    archetype: str
    personality: str
    visual_description: str
    catchphrases: List[str]
    language: str
    tone: str
    # Consistency references
    reference_images: List[str] = None
    lora_path: str = ""
    controlnet_ref: str = ""

    def __post_init__(self):
        if self.reference_images is None:
            self.reference_images = []


class CharacterManager:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.char_config = self.config["character"]
        self.data_dir = Path("data/character")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.character = self._load_or_create_character()

    def _load_or_create_character(self) -> Character:
        char_file = self.data_dir / "character.json"
        if char_file.exists():
            with open(char_file) as f:
                data = json.load(f)
                return Character(**data)
        
        # Create new character from config
        char = Character(
            name=self.char_config["name"],
            archetype=self.char_config["archetype"],
            personality=self.char_config["personality"],
            visual_description=self.char_config["visual_description"],
            catchphrases=self.char_config["catchphrases"],
            language=self.char_config["language"],
            tone=self.char_config["tone"]
        )
        self.save_character(char)
        return char

    def save_character(self, character: Character):
        char_file = self.data_dir / "character.json"
        with open(char_file, 'w') as f:
            json.dump(asdict(character), f, indent=2)

    def get_visual_prompt_base(self) -> str:
        """Base visual prompt for consistent character generation"""
        return (
            f"{self.character.visual_description}, "
            f"same character, consistent appearance, "
            f"high quality, detailed face, sharp focus"
        )

    def get_expression_prompt(self, expression: str) -> str:
        """Get prompt for specific expression"""
        expressions = {
            "judgmental": "judgmental stare, raised eyebrow, unimpressed look, intense eye contact",
            "eye_roll": "rolling eyes, exasperated expression, looking up, annoyed",
            "smirk": "smug smirk, corner of mouth raised, knowing look, confident",
            "facepalm": "facepalm, hand on forehead, disappointed, second-hand embarrassment",
            "shocked": "wide eyes, open mouth, shocked expression, disbelief",
            "laughing": "laughing, mouth open, head tilted back, genuine amusement",
            "confused": "confused expression, tilted head, furrowed brow, questioning",
            "pointing": "pointing at screen, accusatory gesture, calling out"
        }
        expr = expressions.get(expression, "neutral expression")
        return f"{self.get_visual_prompt_base()}, {expr}"

    def get_random_catchphrase(self) -> str:
        return random.choice(self.character.catchphrases)

    def build_comfyui_prompt(self, scene_description: str, expression: str = "judgmental") -> str:
        """Build complete prompt for ComfyUI with character consistency"""
        base = self.get_visual_prompt_base()
        expr = self.get_expression_prompt(expression)
        return f"{base}, {expr}, {scene_description}, cinematic lighting, 8k, highly detailed, sharp focus, 9:16 aspect ratio"

    def build_negative_prompt(self) -> str:
        return (
            "different person, different character, inconsistent face, mutated face, "
            "deformed hands, extra fingers, missing fingers, blurry, low quality, "
            "watermark, text, title, logo, signature, bad anatomy, ugly, distorted, "
            "multiple faces, two faces, different outfit, different hair"
        )

    def get_reference_image_paths(self) -> List[str]:
        """Get paths to reference images for IP-Adapter/ControlNet"""
        ref_dir = self.data_dir / "references"
        if ref_dir.exists():
            return [str(f) for f in ref_dir.glob("*.png")] + [str(f) for f in ref_dir.glob("*.jpg")]
        return []


def main():
    mgr = CharacterManager()
    print(f"Character: {mgr.character.name}")
    print(f"Archetype: {mgr.character.archetype}")
    print(f"Visual: {mgr.character.visual_description[:100]}...")
    print(f"Catchphrases: {mgr.character.catchphrases}")
    print(f"\nJudgmental prompt: {mgr.build_comfyui_prompt('sitting at desk looking at phone screen', 'judgmental')[:200]}...")


if __name__ == "__main__":
    main()