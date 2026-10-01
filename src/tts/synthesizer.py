import subprocess
import tempfile
import os
import yaml
from pathlib import Path
from typing import Optional
from abc import ABC, abstractmethod


class TTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> str:
        pass


class CoquiTTS(TTSEngine):
    def __init__(self, model: str = "tts_models/en/ljspeech/tacotron2-DDC", speaker_wav: Optional[str] = None):
        self.model = model
        self.speaker_wav = speaker_wav
        self._tts = None

    def _load_model(self):
        if self._tts is None:
            from TTS.api import TTS
            self._tts = TTS(self.model, progress_bar=False)

    def synthesize(self, text: str, output_path: str) -> str:
        self._load_model()
        if self.speaker_wav and os.path.exists(self.speaker_wav):
            self._tts.tts_to_file(text=text, file_path=output_path, speaker_wav=self.speaker_wav)
        else:
            self._tts.tts_to_file(text=text, file_path=output_path)
        return output_path


class BarkTTS(TTSEngine):
    def __init__(self, voice_preset: str = "v2/en_speaker_6"):
        self.voice_preset = voice_preset
        self._model = None

    def _load_model(self):
        if self._model is None:
            from bark import generate_audio, preload_models
            preload_models()
            self._model = generate_audio

    def synthesize(self, text: str, output_path: str) -> str:
        self._load_model()
        import numpy as np
        import scipy.io.wavfile as wavfile
        
        audio_array = self._model(text, history_prompt=self.voice_preset)
        sample_rate = 24000
        wavfile.write(output_path, sample_rate, audio_array)
        return output_path


class SystemTTS(TTSEngine):
    def __init__(self, voice: str = "Microsoft Zira Desktop"):
        self.voice = voice

    def synthesize(self, text: str, output_path: str) -> str:
        # Windows: use PowerShell with SpeechSynthesizer
        ps_script = f"""
        Add-Type -AssemblyName System.Speech
        $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
        $synth.SelectVoice('{self.voice}')
        $synth.SetOutputToWaveFile('{output_path}')
        $synth.Speak('{text.replace("'", "''")}')
        $synth.Dispose()
        """
        subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True)
        return output_path


class TTSSynthesizer:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.engine_name = self.config["tts"]["engine"]
        self._engine = self._create_engine()

    def _create_engine(self) -> TTSEngine:
        if self.engine_name == "coqui":
            cfg = self.config["tts"]["coqui"]
            return CoquiTTS(model=cfg["model"], speaker_wav=cfg.get("speaker_wav"))
        elif self.engine_name == "bark":
            cfg = self.config["tts"]["bark"]
            return BarkTTS(voice_preset=cfg["voice_preset"])
        elif self.engine_name == "system":
            cfg = self.config["tts"]["system"]
            return SystemTTS(voice=cfg["voice"])
        else:
            raise ValueError(f"Unknown TTS engine: {self.engine_name}")

    def synthesize(self, text: str, output_path: str) -> str:
        print(f"Synthesizing speech with {self.engine_name}...")
        return self._engine.synthesize(text, output_path)


class VideoAssembler:
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)
        
        self.caption_config = self.config["video_assembly"]
        self.ffmpeg_path = "ffmpeg"

    def add_audio_to_video(self, video_path: str, audio_path: str, output_path: str) -> str:
        """Combine video with TTS audio"""
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", self.caption_config["output_codec"],
            "-preset", self.caption_config["output_preset"],
            "-crf", str(self.caption_config["crf"]),
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-map", "0:v:0",
            "-map", "1:a:0",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def add_captions(self, video_path: str, script: str, output_path: str) -> str:
        """Burn captions into video using FFmpeg drawtext"""
        if not self.caption_config["add_captions"]:
            return video_path
        
        # Create SRT-style caption segments (rough timing based on words)
        words = script.split()
        words_per_second = 2.5  # Average speaking pace
        segment_duration = 3.0  # Seconds per caption segment
        
        # Create temporary ASS subtitle file
        ass_path = video_path.replace(".mp4", "_captions.ass")
        self._create_ass_file(script, ass_path, video_path)
        
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", video_path,
            "-vf", f"ass={ass_path}",
            "-c:v", self.caption_config["output_codec"],
            "-preset", self.caption_config["output_preset"],
            "-crf", str(self.caption_config["crf"]),
            "-c:a", "copy",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Cleanup
        if os.path.exists(ass_path):
            os.remove(ass_path)
        
        return output_path

    def _create_ass_file(self, script: str, ass_path: str, video_path: str):
        """Create ASS subtitle file with word-level timing"""
        # Get video duration
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        
        words = script.split()
        total_words = len(words)
        words_per_segment = max(3, total_words // max(1, int(duration / 3)))
        
        style = self.caption_config["caption_style"]
        
        ass_header = f"""[Script Info]
Title: VideoAI Captions
ScriptType: v4.00+
PlayResX: 576
PlayResY: 1024

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style["font"]},{style["fontsize"]},&H{self._rgb_to_ass(style["color"])},&H{self._rgb_to_ass(style["color"])},&H{self._rgb_to_ass(style["outline_color"])},&H00000000,-1,0,0,0,100,100,0,0,1,{style["outline_width"]},0,2,20,20,{style["margin_bottom"]},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        dialogues = []
        current_time = 0.0
        for i in range(0, total_words, words_per_segment):
            segment_words = words[i:i + words_per_segment]
            segment_text = " ".join(segment_words)
            segment_duration = len(segment_words) / words_per_second
            end_time = min(current_time + segment_duration, duration)
            
            start_str = self._seconds_to_ass_time(current_time)
            end_str = self._seconds_to_ass_time(end_time)
            
            dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{segment_text}")
            current_time = end_time
            if current_time >= duration:
                break
        
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(ass_header + "\n".join(dialogues))

    def _rgb_to_ass(self, color: str) -> str:
        """Convert color name to ASS format (BBGGRR)"""
        color_map = {
            "white": "FFFFFF",
            "black": "000000",
            "red": "0000FF",
            "green": "00FF00",
            "blue": "FF0000",
            "yellow": "00FFFF",
        }
        return color_map.get(color.lower(), "FFFFFF")

    def _seconds_to_ass_time(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds - int(seconds)) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def assemble_final_video(self, video_path: str, script: str, output_dir: str = "data/videos") -> str:
        """Full pipeline: TTS -> combine -> captions"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        base_name = Path(video_path).stem
        final_path = Path(output_dir) / f"{base_name}_final.mp4"
        
        # Step 1: Generate TTS audio
        tts = TTSSynthesizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_audio:
            audio_path = tmp_audio.name
        
        try:
            tts.synthesize(script, audio_path)
            
            # Step 2: Combine video + audio
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp_combined:
                combined_path = tmp_combined.name
            
            self.add_audio_to_video(video_path, audio_path, combined_path)
            
            # Step 3: Add captions
            self.add_captions(combined_path, script, str(final_path))
            
            # Cleanup temp files
            os.unlink(audio_path)
            os.unlink(combined_path)
            
        except Exception as e:
            # Cleanup on error
            for p in [audio_path, combined_path]:
                if os.path.exists(p):
                    os.unlink(p)
            raise
        
        return str(final_path)


def main():
    # Test
    assembler = VideoAssembler()
    test_video = "data/videos/test.mp4"  # Would need a real video
    test_script = "This is a test script for the video assembly pipeline."
    
    if os.path.exists(test_video):
        result = assembler.assemble_final_video(test_video, test_script)
        print(f"Final video: {result}")
    else:
        print("Test video not found, skipping assembly test")


if __name__ == "__main__":
    main()