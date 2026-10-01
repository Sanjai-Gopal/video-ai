import json
import random
import requests
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class VideoConcept:
    title: str
    topic: str
    script: str
    video_prompt: str
    niche: str
    affiliate_cta: str
    created_at: str


class ContentIdeation:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.ollama_host = self.config["ollama"]["host"]
        self.model = self.config["ollama"]["model"]
        self.temperature = self.config["ollama"]["temperature"]
        self.max_tokens = self.config["ollama"]["max_tokens"]
        self.niches = self.config["niches"]
        self.affiliate_cta = self.config["monetization"]["cta_text"]
        self.affiliate_links = self.config["monetization"]["affiliate_links"]

    def _get_random_niche(self) -> str:
        return random.choice(self.niches)

    def _build_prompt(self, niche: str) -> str:
        affiliate_text = "\n".join([f"- {link['name']}: {link['url']} ({link['description']})" for link in self.affiliate_links])
        
        return f"""You are a viral short-form content strategist for YouTube Shorts, Instagram Reels, and Facebook Reels.

NICHE: {niche}

Create ONE highly engaging 20-30 second video concept optimized for retention (hook in first 2 seconds).

Return ONLY valid JSON with these exact keys:
{{
  "title": "Short catchy title (max 60 chars)",
  "topic": "Topic name",
  "script": "20-30 second voiceover script. Conversational, energetic, with clear hook, value, and CTA.",
  "video_prompt": "Detailed visual prompt for AI video generation (AnimateDiff/SVD). Describe: scenes, camera angles, lighting, colors, motion, style. 8 seconds, 9:16 aspect ratio."
}}

AFFILIATE CTA TO INCLUDE IN SCRIPT: "{self.affiliate_cta}"

AVAILABLE AFFILIATE LINKS (reference in script naturally):
{affiliate_text}

RULES:
- Hook in first 2 seconds (question, shock, curiosity)
- One clear value/insight per video
- Natural affiliate mention (not salesy)
- Script: ~60-80 words for 20-30 sec at normal pace
- Video prompt: photorealistic or cinematic style, specific movements
- No markdown, no extra text, just JSON"""

    def generate_concept(self, niche: Optional[str] = None) -> VideoConcept:
        niche = niche or self._get_random_niche()
        prompt = self._build_prompt(niche)
        
        response = requests.post(
            f"{self.ollama_host}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": False,
                "format": "json"
            },
            timeout=self.config["ollama"]["timeout"]
        )
        response.raise_for_status()
        result = response.json()
        
        try:
            data = json.loads(result["response"])
        except json.JSONDecodeError:
            # Fallback: try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', result["response"], re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"Failed to parse JSON from LLM: {result['response']}")
        
        concept = VideoConcept(
            title=data["title"].strip(),
            topic=data["topic"].strip(),
            script=data["script"].strip(),
            video_prompt=data["video_prompt"].strip(),
            niche=niche,
            affiliate_cta=self.affiliate_cta,
            created_at=datetime.now().isoformat()
        )
        
        return concept

    def save_concept(self, concept: VideoConcept, output_dir: str = "data/logs") -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        filename = f"concept_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(output_dir) / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(concept), f, indent=2)
        
        return str(filepath)


def main():
    ideation = ContentIdeation()
    concept = ideation.generate_concept()
    filepath = ideation.save_concept(concept)
    print(f"Generated concept: {concept.title}")
    print(f"Saved to: {filepath}")
    print(json.dumps(asdict(concept), indent=2))


if __name__ == "__main__":
    main()