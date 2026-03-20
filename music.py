import os
import uuid
import httpx
from typing import Optional

MUSIC_OUTPUT_DIR = os.getenv("MUSIC_OUTPUT_DIR", "./audio_output")
os.makedirs(MUSIC_OUTPUT_DIR, exist_ok=True)

# HuggingFace Inference API — free tier, no local install needed
# Get your free token at huggingface.co/settings/tokens
HF_TOKEN  = os.getenv("HF_TOKEN", "")
HF_URL    = "https://api-inference.huggingface.co/models/facebook/musicgen-small"

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


def mood_to_musicgen_prompt(
    mood_tag: str,
    bpm: int,
    style_keywords: list,
    spotify_taste: Optional[dict] = None,
) -> str:
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


def get_preset(vibe: str, spotify_taste: Optional[dict] = None) -> dict:
    preset = VIBE_PRESETS.get(vibe, VIBE_PRESETS["ultra_focus"]).copy()
    bpm = preset["bpm"]
    if spotify_taste and spotify_taste.get("avg_bpm"):
        bpm = int(bpm + (spotify_taste["avg_bpm"] - bpm) * 0.15)
        bpm = max(50, min(90, bpm))
    prompt = preset["prompt"]
    return {
        "mood_tag":       preset["mood_tag"],
        "bpm":            bpm,
        "energy_level":   preset["energy_level"],
        "style_keywords": preset["style_keywords"],
        "music_prompt":   prompt,
    }


async def generate_audio(prompt: str, duration: int = 30) -> str:
    """
    Call HuggingFace Inference API for MusicGen.
    Returns path to saved .wav file.

    Get free HF token at huggingface.co/settings/tokens
    Add to .env: HF_TOKEN=hf_...
    """
    filename = str(uuid.uuid4())
    output_path = os.path.join(MUSIC_OUTPUT_DIR, f"{filename}.wav")

    headers = {}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            HF_URL,
            headers=headers,
            json={
                "inputs": prompt,
                "parameters": {"max_new_tokens": duration * 50},
            },
        )

        if response.status_code == 503:
            # Model is loading — happens on first call, wait and retry
            raise Exception("MusicGen model is loading on HuggingFace, wait 20 seconds and try again")

        if response.status_code != 200:
            raise Exception(f"HuggingFace API error: {response.status_code} — {response.text}")

        # Save audio bytes to file
        with open(output_path, "wb") as f:
            f.write(response.content)

    return output_path