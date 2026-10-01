import json
import time
import requests
import uuid
import yaml
import websocket
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class VideoClip:
    prompt: str
    expression: str
    description: str
    duration: str
    local_path: str = ""


class ComfyUIVideoGenerator:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.host = self.config["comfyui"]["host"]
        self.workflow_path = Path("comfyui_workflows") / self.config["comfyui"]["workflow"]
        self.timeout = self.config["comfyui"]["timeout"]
        self.width = self.config["comfyui"]["width"]
        self.height = self.config["comfyui"]["height"]
        self.fps = self.config["comfyui"]["fps"]
        
        with open(self.workflow_path) as f:
            self.base_workflow = json.load(f)

    def _inject_prompts(self, positive_prompt: str, negative_prompt: str) -> dict:
        workflow = json.loads(json.dumps(self.base_workflow))
        
        for node_id, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncode":
                title = node.get("_meta", {}).get("title", "")
                if "Positive" in title:
                    node["inputs"]["text"] = positive_prompt
                elif "Negative" in title:
                    node["inputs"]["text"] = negative_prompt
            elif node.get("class_type") == "EmptyLatentImage":
                node["inputs"]["width"] = self.width
                node["inputs"]["height"] = self.height
            elif node.get("class_type") == "VHS_VideoCombine":
                node["inputs"]["fps"] = self.fps
        
        return workflow

    def queue_prompt(self, workflow: dict) -> str:
        prompt_id = str(uuid.uuid4())
        response = requests.post(
            f"{self.host}/prompt",
            json={"prompt": workflow, "client_id": prompt_id},
            timeout=30
        )
        response.raise_for_status()
        return response.json()["prompt_id"]

    def wait_for_completion(self, prompt_id: str) -> dict:
        ws_url = self.host.replace("http", "ws") + f"/ws?clientId={prompt_id}"
        ws = websocket.create_connection(ws_url)
        
        try:
            while True:
                msg = json.loads(ws.recv())
                if msg["type"] == "executing":
                    data = msg["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break
                elif msg["type"] == "progress":
                    val = msg['data']['value']
                    max_v = msg['data']['max']
                    if max_v > 0:
                        print(f"  Progress: {val}/{max_v}")
        finally:
            ws.close()
        
        response = requests.get(f"{self.host}/history/{prompt_id}", timeout=30)
        response.raise_for_status()
        history = response.json()
        
        if prompt_id not in history:
            raise RuntimeError("Prompt not found in history")
        
        return history[prompt_id]

    def get_output_video(self, history: dict, output_dir: str = "data/videos") -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        outputs = history.get("outputs", {})
        for node_id, node_output in outputs.items():
            if "videos" in node_output:
                for video in node_output["videos"]:
                    filename = video["filename"]
                    subfolder = video.get("subfolder", "")
                    url = f"{self.host}/view?filename={filename}&subfolder={subfolder}&type=output"
                    
                    response = requests.get(url, stream=True, timeout=60)
                    response.raise_for_status()
                    
                    local_path = Path(output_dir) / filename
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    return str(local_path)
        
        raise RuntimeError("No video output found in history")

    def generate_clip(self, positive_prompt: str, negative_prompt: str, output_dir: str = "data/videos") -> str:
        workflow = self._inject_prompts(positive_prompt, negative_prompt)
        prompt_id = self.queue_prompt(workflow)
        print(f"  Queued: {prompt_id}")
        
        history = self.wait_for_completion(prompt_id)
        video_path = self.get_output_video(history, output_dir)
        print(f"  Generated: {video_path}")
        
        return video_path

    def generate_script_clips(self, script, character_manager, output_dir: str = "data/videos") -> List[VideoClip]:
        """Generate all clips for a script"""
        clips = []
        negative_prompt = character_manager.build_negative_prompt()
        
        for i, (line, cue) in enumerate(zip(script.roast_lines, script.visual_cues)):
            expression = cue.get("expression", "judgmental")
            description = cue.get("description", f"Character reacting: {line}")
            
            positive_prompt = character_manager.build_comfyui_prompt(description, expression)
            
            print(f"Generating clip {i+1}/{len(script.roast_lines)}: {expression}")
            clip_path = self.generate_clip(positive_prompt, negative_prompt, output_dir)
            
            clips.append(VideoClip(
                prompt=positive_prompt,
                expression=expression,
                description=description,
                duration=cue.get("duration", "3s"),
                local_path=clip_path
            ))
        
        return clips


def main():
    from src.character.character_manager import CharacterManager
    
    char_mgr = CharacterManager()
    gen = ComfyUIVideoGenerator()
    
    # Test single clip
    test_prompt = char_mgr.build_comfyui_prompt("sitting at desk looking at phone with judgmental stare", "judgmental")
    test_neg = char_mgr.build_negative_prompt()
    
    print("Testing single clip generation...")
    try:
        path = gen.generate_clip(test_prompt, test_neg)
        print(f"Success: {path}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure ComfyUI is running on port 8188")


if __name__ == "__main__":
    main()