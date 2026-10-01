import subprocess
import tempfile
import os
import yaml
import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ClipInfo:
    path: str
    duration: float
    text: str
    expression: str


class AutoEditor:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.editor_config = self.config["editor"]
        self.ffmpeg = "ffmpeg"
        self.template_dir = Path("templates")
        self.template_dir.mkdir(exist_ok=True)
        self._create_default_template()

    def _create_default_template(self):
        """Create default editor template config"""
        template = {
            "intro": {
                "duration": self.editor_config["intro_duration"],
                "text": "ROAST TIME",
                "animation": "zoom_in"
            },
            "caption_style": self.editor_config["caption_style"],
            "watermark": {
                "enabled": self.editor_config["add_watermark"],
                "text": self.editor_config["watermark"],
                "position": "bottom_right",
                "opacity": 0.7
            },
            "music": {
                "enabled": True,
                "volume": self.editor_config["music_volume"],
                "track": "assets/background_music.mp3"
            },
            "outro": {
                "duration": self.editor_config["outro_duration"],
                "text": "FOLLOW FOR MORE ROASTS",
                "animation": "fade_out"
            }
        }
        
        template_path = self.template_dir / "roaster_template.json"
        with open(template_path, 'w') as f:
            json.dump(template, f, indent=2)

    def get_video_duration(self, video_path: str) -> float:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())

    def create_caption_ass(self, clips: List[ClipInfo], output_path: str, video_width: int = 576, video_height: int = 1024):
        """Create ASS subtitle file with styled captions"""
        style = self.editor_config["caption_style"]
        
        ass_header = f"""[Script Info]
Title: RoastBot Captions
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style["font"]},{style["fontsize"]},&H{self._rgb_to_ass(style["color"])},&H{self._rgb_to_ass(style["color"])},&H{self._rgb_to_ass(style["stroke_color"])},&H00000000,-1,0,0,0,100,100,0,0,1,{style["stroke_width"]},2,2,20,20,100,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        dialogues = []
        current_time = 0.0
        
        for clip in clips:
            duration = clip.duration
            end_time = current_time + duration
            
            start_str = self._seconds_to_ass_time(current_time)
            end_str = self._seconds_to_ass_time(end_time)
            
            # Add expression indicator
            text = clip.text
            if clip.expression:
                text = f"[{clip.expression.upper()}] {text}"
            
            dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")
            current_time = end_time
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ass_header + "\n".join(dialogues))

    def _rgb_to_ass(self, color: str) -> str:
        color_map = {
            "white": "FFFFFF",
            "black": "000000",
            "red": "0000FF",
            "yellow": "00FFFF",
            "green": "00FF00",
            "blue": "FF0000"
        }
        return color_map.get(color.lower(), "FFFFFF")

    def _seconds_to_ass_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds - int(seconds)) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def add_background_music(self, video_path: str, music_path: str, output_path: str, volume: float = 0.15):
        """Mix background music with video"""
        if not os.path.exists(music_path):
            # Create silent audio if no music
            subprocess.run([
                self.ffmpeg, "-y", "-i", video_path,
                "-c", "copy", output_path
            ], check=True, capture_output=True)
            return output_path
        
        cmd = [
            self.ffmpeg, "-y",
            "-i", video_path,
            "-stream_loop", "-1", "-i", music_path,
            "-filter_complex", f"[1:a]volume={volume}[music];[0:a][music]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def add_watermark(self, video_path: str, output_path: str, watermark_text: str = "@RoastBot"):
        """Add text watermark"""
        cmd = [
            self.ffmpeg, "-y",
            "-i", video_path,
            "-vf", f"drawtext=text='{watermark_text}':fontfile=Arial:fontsize=24:fontcolor=white@0.7:x=w-tw-20:y=h-th-20",
            "-c:a", "copy",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def create_intro_outro(self, intro_text: str, outro_text: str, width: int, height: int, 
                           intro_path: str, outro_path: str, duration: float = 0.5):
        """Create simple intro/outro clips"""
        # Intro
        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi", "-i", f"color=black:size={width}x{height}:duration={duration}:rate=30",
            "-vf", f"drawtext=text='{intro_text}':fontfile=Impact:fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            intro_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Outro
        cmd = [
            self.ffmpeg, "-y",
            "-f", "lavfi", "-i", f"color=black:size={width}x{height}:duration={duration}:rate=30",
            "-vf", f"drawtext=text='{outro_text}':fontfile=Impact:fontsize=60:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            outro_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def assemble_final_video(self, clips: List[ClipInfo], script, output_dir: str = "data/videos") -> str:
        """Full assembly: concat clips + captions + music + watermark + intro/outro"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        base_name = f"final_{script.topic[:30].replace(' ', '_')}_{len(clips)}clips"
        final_path = Path(output_dir) / f"{base_name}.mp4"
        
        # Create concat file
        concat_file = Path(output_dir) / f"concat_{base_name}.txt"
        with open(concat_file, 'w') as f:
            for clip in clips:
                f.write(f"file '{clip.path}'\n")
        
        # Step 1: Concatenate clips
        concat_video = Path(output_dir) / f"concat_{base_name}.mp4"
        cmd = [
            self.ffmpeg, "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-c", "copy",
            str(concat_video)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Step 2: Add captions
        ass_file = Path(output_dir) / f"captions_{base_name}.ass"
        self.create_caption_ass(clips, str(ass_file))
        
        captioned_video = Path(output_dir) / f"captioned_{base_name}.mp4"
        cmd = [
            self.ffmpeg, "-y",
            "-i", str(concat_video),
            "-vf", f"ass={ass_file}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "copy",
            str(captioned_video)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Step 3: Add background music
        music_path = self.template_dir / "background_music.mp3"
        musiced_video = Path(output_dir) / f"music_{base_name}.mp4"
        self.add_background_music(str(captioned_video), str(music_path), str(musiced_video))
        
        # Step 4: Add watermark
        if self.editor_config["add_watermark"]:
            watermarked_video = Path(output_dir) / f"watermarked_{base_name}.mp4"
            self.add_watermark(str(musiced_video), str(watermarked_video), self.editor_config["watermark"])
            musiced_video = watermarked_video
        
        # Step 5: Add intro/outro
        intro_path = Path(output_dir) / f"intro_{base_name}.mp4"
        outro_path = Path(output_dir) / f"outro_{base_name}.mp4"
        
        self.create_intro_outro(
            "ROAST TIME", 
            "FOLLOW FOR MORE ROASTS", 
            self.config["comfyui"]["width"], 
            self.config["comfyui"]["height"],
            str(intro_path), str(outro_path),
            self.editor_config["intro_duration"]
        )
        
        # Final concat with intro/outro
        final_concat = Path(output_dir) / f"final_concat_{base_name}.txt"
        with open(final_concat, 'w') as f:
            f.write(f"file '{intro_path}'\n")
            f.write(f"file '{musiced_video}'\n")
            f.write(f"file '{outro_path}'\n")
        
        cmd = [
            self.ffmpeg, "-y",
            "-f", "concat", "-safe", "0", "-i", str(final_concat),
            "-c", "copy",
            str(final_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Cleanup temp files
        for f in [concat_file, concat_video, ass_file, captioned_video, musiced_video, intro_path, outro_path, final_concat]:
            if f.exists() and f != final_path:
                f.unlink(missing_ok=True)
        
        return str(final_path)


def main():
    editor = AutoEditor()
    print("AutoEditor initialized")
    print("Templates:", list(editor.template_dir.glob("*.json")))


if __name__ == "__main__":
    main()