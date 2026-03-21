import os
import uuid
import scipy
import numpy as np
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

MUSIC_OUTPUT_DIR = os.getenv("MUSIC_OUTPUT_DIR", "./audio_output")
os.makedirs(MUSIC_OUTPUT_DIR, exist_ok=True)

_model = None
_processor = None

VIBE_PRESETS = {
    "ultra_focus": {
        "mood_tag":       "deep_focus",
        "bpm":            55,
        "energy_level":   0.2,
        "style_keywords": ["minimal piano", "no melody", "sparse", "drone", "no drums"],
        "prompt":         "minimal piano 55bpm no melody sparse drone texture deep concentration study music no drums no vocals",
    },
    "deep_calm": {
        "mood_tag":       "deep_calm",
        "bpm":            62,
        "energy_level":   0.25,
        "style_keywords": ["soft ambient", "calm", "nature sounds", "no beat", "peaceful"],
        "prompt":         "soft ambient 62bpm calm nature sounds peaceful no beat no drums instrumental relaxing study",
    },
    "exam_crunch": {
        "mood_tag":       "exam_crunch",
        "bpm":            58,
        "energy_level":   0.35,
        "style_keywords": ["tense focus", "minimal", "urgent", "sparse piano"],
        "prompt":         "tense minimal piano 58bpm urgent focus no distraction sparse no vocals study music",
    },
    "light_review": {
        "mood_tag":       "light_review",
        "bpm":            75,
        "energy_level":   0.45,
        "style_keywords": ["warm lo-fi", "gentle guitar", "relaxed", "easy flow"],
        "prompt":         "warm lo-fi 75bpm gentle acoustic guitar relaxed easy flow soft beat chill study music",
    },
    "creative_flow": {
        "mood_tag":       "creative_flow",
        "bpm":            72,
        "energy_level":   0.55,
        "style_keywords": ["jazz lo-fi", "upbeat", "creative", "light jazz"],
        "prompt":         "jazz lo-fi 72bpm upbeat creative productive light jazz piano study music",
    },
    "memory_mode": {
        "mood_tag":       "memory_mode",
        "bpm":            65,
        "energy_level":   0.3,
        "style_keywords": ["drone waves", "repetitive", "hypnotic", "soft texture"],
        "prompt":         "drone waves 65bpm repetitive hypnotic soft texture memory focus no melody ambient study",
    },
}


def _load_model():
    global _model, _processor
    if _model is None:
        print("Loading MusicGen model — first time takes 1-2 minutes, please wait...")
        from transformers import AutoProcessor, MusicgenForConditionalGeneration
        _processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
        _model     = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
        print("MusicGen model loaded and ready!")
    return _processor, _model


def mood_to_musicgen_prompt(mood_tag, bpm, style_keywords, spotify_taste=None):
    keywords_str = ", ".join(style_keywords)
    prompt = f"{keywords_str}, {bpm}bpm, study music, instrumental"
    if spotify_taste:
        if spotify_taste.get("instrumentalness", 0) > 0.6:
            prompt += ", no vocals, purely instrumental"
        if spotify_taste.get("acousticness", 0) > 0.6:
            prompt += ", acoustic instruments"
        genres = spotify_taste.get("top_genres", [])
        if any("jazz" in g for g in genres):
            prompt += ", jazz influenced"
        if any(g in ["lo-fi", "lofi", "chillhop"] for g in genres):
            prompt += ", lo-fi aesthetic"
    prompt += ", high quality"
    return prompt


def get_preset(vibe, spotify_taste=None):
    preset = VIBE_PRESETS.get(vibe, VIBE_PRESETS["ultra_focus"]).copy()
    bpm = preset["bpm"]
    if spotify_taste and spotify_taste.get("avg_bpm"):
        bpm = int(bpm + (spotify_taste["avg_bpm"] - bpm) * 0.15)
        bpm = max(50, min(90, bpm))
    return {
        "mood_tag":       preset["mood_tag"],
        "bpm":            bpm,
        "energy_level":   preset["energy_level"],
        "style_keywords": preset["style_keywords"],
        "music_prompt":   preset["prompt"],
    }


async def generate_audio(prompt: str, duration: int = 30) -> str:
    processor, model = _load_model()

    # ~51 tokens per second, max 1503 tokens (~30s)
    max_tokens = min(duration * 51, 1503)

    inputs = processor(
        text=[prompt],
        padding=True,
        return_tensors="pt",
    )

    audio_values = model.generate(
        **inputs,
        do_sample=True,
        guidance_scale=3,
        max_new_tokens=max_tokens,
    )

    filename      = str(uuid.uuid4())
    output_path   = os.path.join(MUSIC_OUTPUT_DIR, f"{filename}.wav")
    sampling_rate = model.config.audio_encoder.sampling_rate

    scipy.io.wavfile.write(
        output_path,
        rate=sampling_rate,
        data=audio_values[0, 0].numpy(),
    )

    return output_path