import json
import time
import requests
import uuid
import yaml
from pathlib import Path
from typing import Optional
import websocket
import threading


class ComfyUIVideoGenerator:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.host = self.config["comfyui"]["host"]
        self.workflow_path = Path("comfyui_workflows") / self.config["comfyui"]["workflow"]
        self.timeout = self.config["comfyui"]["timeout"]
        self.video_length = self.config["comfyui"]["video_length"]
        self.fps = self.config["comfyui"]["fps"]
        self.width = self.config["comfyui"]["width"]
        self.height = self.config["comfyui"]["height"]
        
        with open(self.workflow_path) as f:
            self.base_workflow = json.load(f)

    def _inject_prompt(self, prompt: str) -> dict:
        workflow = json.loads(json.dumps(self.base_workflow))  # Deep copy
        
        # Find and update the positive prompt node
        for node_id, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncode" and "Positive" in node.get("_meta", {}).get("title", ""):
                node["inputs"]["text"] = f"{prompt}, masterpiece, best quality, cinematic lighting, 8k, highly detailed, smooth motion, 9:16 aspect ratio"
                break
        
        # Update video settings
        for node_id, node in workflow.items():
            if node.get("class_type") == "EmptyLatentImage":
                node["inputs"]["width"] = self.width
                node["inputs"]["height"] = self.height
            if node.get("class_type") == "VHS_VideoCombine":
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
        ws = websocket.create_connection(f"{self.host.replace('http', 'ws')}/ws?clientId={prompt_id}")
        
        try:
            while True:
                msg = json.loads(ws.recv())
                if msg["type"] == "executing":
                    data = msg["data"]
                    if data["node"] is None and data["prompt_id"] == prompt_id:
                        break
                elif msg["type"] == "progress":
                    print(f"Progress: {msg['data']['value']}/{msg['data']['max']}")
        finally:
            ws.close()
        
        # Get the output
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

    def generate(self, prompt: str, output_dir: str = "data/videos") -> str:
        print(f"Generating video with prompt: {prompt[:100]}...")
        
        workflow = self._inject_prompt(prompt)
        prompt_id = self.queue_prompt(workflow)
        print(f"Queued prompt: {prompt_id}")
        
        history = self.wait_for_completion(prompt_id)
        print("Generation complete, downloading...")
        
        video_path = self.get_output_video(history, output_dir)
        print(f"Video saved to: {video_path}")
        
        return video_path


def main():
    # Test with a sample prompt
    generator = ComfyUIVideoGenerator()
    test_prompt = "A futuristic AI robot working on a laptop, neon blue and purple lighting, camera slowly orbits around, smooth cinematic motion, 8k photorealistic"
    try:
        video_path = generator.generate(test_prompt)
        print(f"Success: {video_path}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure ComfyUI is running on http://localhost:8188")


if __name__ == "__main__":
    main()