import yaml
import json
import requests
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path


@dataclass
class RoastScript:
    topic: str
    category: str
    hook: str
    roast_lines: List[str]
    visual_cues: List[Dict[str, str]]  # {expression, description, duration}
    catchphrase: str
    cta: str
    hashtags: List[str]
    title: str
    created_at: str


class RoastScriptGenerator:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.ollama_host = self.config["ollama"]["host"]
        self.model = self.config["ollama"]["model"]
        self.temperature = self.config["ollama"]["temperature"]
        self.max_tokens = self.config["ollama"]["max_tokens"]
        self.timeout = self.config["ollama"]["timeout"]
        
        self.character_name = self.config["character"]["name"]
        self.catchphrases = self.config["character"]["catchphrases"]
        self.categories = self.config["content_sources"]["roast_categories"]
        self.cta_variations = self.config["monetization"]["cta_variations"]
        self.affiliate_links = self.config["monetization"]["affiliate_links"]

    def _get_trending_topic(self) -> Dict[str, str]:
        """Generate a trending topic to roast based on category"""
        category = random.choice(self.categories)
        
        topics_by_category = {
            "cringe_reels": [
                "that guy acting like a CEO in his bedroom",
                "girl doing 50 transitions for a 3 second reel",
                "couple doing cringe dance in metro",
                "uncle trying to be cool with gen z slang"
            ],
            "fake_gurus": [
                "19 year old selling 'how to make 1 crore' course",
                "'business coach' who never ran a business",
                "'mindset guru' charging 50k for 'wake up at 5am'",
                "'crypto expert' who bought at ATH"
            ],
            "bollywood_logic": [
                "hero falls from helicopter, lands on feet, hair perfect",
                "villain explains entire plan instead of killing hero",
                "mother recognizes son by 'birthmark' after 20 years",
                "train catches up to hero running at 200kmph"
            ],
            "influencer_scams": [
                "influencer selling 'glow water' for 5000 rs",
                "'giveaway' that requires following 50 accounts",
                "beauty filter vs reality exposed",
                "promoting app that steals your data"
            ],
            "viral_challenges": [
                "eating tide pods challenge but indian version",
                "jumping off moving train for reel",
                "destroying public property for views",
                "fake prank on parents gone wrong"
            ],
            "relatable_struggles": [
                "indian mom calling 50 times when you're 5 min late",
                "auto driver saying 'meter nahi chalega'",
                "zomato delivery guy calling 'sir location batao'",
                "studying all night, exam questions from chapter you skipped"
            ],
            "tech_scams": [
                "laptop scheme for students that's actually a scam",
                "'free iphone' link in bio",
                "crypto trading bot guaranteed 100% returns",
                "AI tool that 'writes code for you' but copies stackoverflow"
            ],
            "education_system": [
                "college placement cell: 'package 3 lpa, work 14 hours'",
                "professor reading slides word by word",
                "attendance 75% mandatory but classes at 8am",
                "final year project: 'download from github, change name'"
            ]
        }
        
        topic = random.choice(topics_by_category.get(category, topics_by_category["relatable_struggles"]))
        return {"topic": topic, "category": category}

    def _build_prompt(self, topic_data: Dict[str, str]) -> str:
        catchphrases_str = ", ".join(self.catchphrases)
        cta = random.choice(self.cta_variations)
        
        return f"""You are {self.character_name}, a savage Indian Gen Z roaster who destroys cringe content, fake gurus, Bollywood logic, and internet scams.

TARGET TOPIC: {topic_data['topic']}
CATEGORY: {topic_data['category']}

Create a 30-45 second ROAST script for YouTube Shorts/Reels/TikTok.

RETURN ONLY VALID JSON with these exact keys:
{{
  "hook": "First 3 seconds - visual + verbal hook that stops scroll",
  "roast_lines": ["line1", "line2", "line3", "line4", "line5"],
  "visual_cues": [
    {{"expression": "judgmental", "description": "what character does on screen", "duration": "3s"}},
    {{"expression": "eye_roll", "description": "character reaction", "duration": "3s"}}
  ],
  "cta": "{cta}",
  "hashtags": ["roast", "commentary", "viral", "trends", "india"]
}}

RULES:
- Hinglish language (Hindi + English mix)
- Savage but relatable, not offensive
- 5-6 roast lines max, each 2-3 seconds
- Each line needs matching visual cue with expression
- Expressions: judgmental, eye_roll, smirk, facepalm, shocked, laughing, confused, pointing
- Hook must be visual + verbal combo
- Include ONE catchphrase naturally: {catchphrases_str}
- CTA: "{cta}"
- 5-7 hashtags max
- Title: catchy, under 60 chars
- NO markdown, NO extra text, ONLY JSON"""

    def generate_script(self, topic_data: Optional[Dict] = None) -> RoastScript:
        topic_data = topic_data or self._get_trending_topic()
        prompt = self._build_prompt(topic_data)
        
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
            timeout=self.timeout
        )
        response.raise_for_status()
        result = response.json()
        
        try:
            data = json.loads(result["response"])
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{.*\}', result["response"], re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                raise ValueError(f"Failed to parse JSON: {result['response']}")
        
        script = RoastScript(
            topic=topic_data["topic"],
            category=topic_data["category"],
            hook=data["hook"],
            roast_lines=data["roast_lines"],
            visual_cues=data["visual_cues"],
            catchphrase=random.choice(self.catchphrases),
            cta=data.get("cta", random.choice(self.cta_variations)),
            hashtags=data.get("hashtags", ["roast", "commentary", "viral", "india"]),
            title=data.get("title", f"Roasting: {topic_data['topic'][:40]}"),
            created_at=datetime.now().isoformat()
        )
        
        return script

    def save_script(self, script: RoastScript, output_dir: str = "data/logs") -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        filename = f"script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = Path(output_dir) / filename
        
        with open(filepath, 'w') as f:
            json.dump(asdict(script), f, indent=2)
        
        return str(filepath)

    def generate_batch(self, count: int = 4) -> List[RoastScript]:
        scripts = []
        for _ in range(count):
            script = self.generate_script()
            scripts.append(script)
            self.save_script(script)
        return scripts


def main():
    gen = RoastScriptGenerator()
    scripts = gen.generate_batch(2)
    for i, s in enumerate(scripts, 1):
        print(f"\n--- Script {i} ---")
        print(f"Title: {s.title}")
        print(f"Topic: {s.topic}")
        print(f"Hook: {s.hook}")
        for j, line in enumerate(s.roast_lines):
            print(f"  {j+1}. {line}")
        print(f"CTA: {s.cta}")
        print(f"Hashtags: {s.hashtags}")


if __name__ == "__main__":
    main()