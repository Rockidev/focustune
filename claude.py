import anthropic
import json
import os
from typing import Optional

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MOOD_TAGS = ["deep_focus", "exam_crunch", "light_review", "deep_calm", "creative_flow", "memory_mode"]

BASE_SYSTEM = """You are a music mood analyzer for PadhaiBeats — a study music app for Indian students.

Analyze the student's study session description and return a JSON object ONLY.
No explanation, no markdown, no extra text. Pure JSON.

Return exactly this structure:
{
  "mood_tag": one of [deep_focus, exam_crunch, light_review, deep_calm, creative_flow, memory_mode],
  "bpm": integer between 50 and 90,
  "energy_level": float between 0.1 and 0.9,
  "style_keywords": list of 4-6 music style words,
  "reasoning": one short sentence explaining why
}

Mood tag guide:
- deep_focus: complex technical topics, algorithms, maths, JEE physics
- exam_crunch: high stress, exam tomorrow, need to focus fast, panic revision
- light_review: easy revision, already know the topic, relaxed mood
- deep_calm: long reading sessions, NEET bio, low stress, slow pace
- creative_flow: assignments, projects, writing, MBA case studies
- memory_mode: memorising facts, dates, diagrams, vocabulary

BPM guide:
- deep_focus / exam_crunch: 52-62
- deep_calm / memory_mode: 60-68
- light_review / creative_flow: 70-82

Style keyword examples: minimal piano, sparse, no melody, ambient drone, soft lo-fi,
warm guitar, jazz lo-fi, nature sounds, binaural texture, instrumental, no vocals, no drums"""


def build_personalization_block(spotify_taste: Optional[dict], learned_prefs: Optional[dict]) -> str:
    lines = []
    if spotify_taste:
        lines.append("\n--- This user's music taste from Spotify ---")
        lines.append(f"Their avg BPM in real life: {spotify_taste.get('avg_bpm', 'unknown')}")
        lines.append(f"Energy preference: {spotify_taste.get('energy', 'unknown')} / 1.0")
        lines.append(f"Prefers instrumental: {spotify_taste.get('instrumentalness', 0) > 0.5}")
        genres = spotify_taste.get("top_genres", [])
        if genres:
            lines.append(f"Top genres: {', '.join(genres[:3])}")
        lines.append("Use this to nudge BPM and style closer to their natural taste.")
    if learned_prefs and learned_prefs.get("sample_count", 0) >= 3:
        lines.append("\n--- What this user has liked while studying ---")
        if learned_prefs.get("preferred_bpm"):
            lines.append(f"Their preferred study BPM so far: {learned_prefs['preferred_bpm']:.0f}")
        top_kw = learned_prefs.get("top_keywords", [])
        if top_kw:
            lines.append(f"Style keywords they loved: {', '.join(top_kw[:4])}")
        avoided_kw = learned_prefs.get("avoided_keywords", [])
        if avoided_kw:
            lines.append(f"Style keywords they skipped: {', '.join(avoided_kw[:3])}")
    return "\n".join(lines)


async def analyze_description(
    description: str,
    language: str = "auto",
    spotify_taste: Optional[dict] = None,
    learned_prefs: Optional[dict] = None,
) -> dict:
    personalization = build_personalization_block(spotify_taste, learned_prefs)
    system_prompt = BASE_SYSTEM + personalization

    lang_hint = ""
    if language == "hindi":
        lang_hint = "\nNote: The description is in Hindi. Understand it fully before analyzing."
    elif language == "hinglish":
        lang_hint = "\nNote: The description is in Hinglish (Hindi + English mix). Understand it fully."

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=system_prompt + lang_hint,
        messages=[{"role": "user", "content": f"Student's study session: {description}"}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    mood_data = json.loads(raw)
    if mood_data.get("mood_tag") not in MOOD_TAGS:
        mood_data["mood_tag"] = "deep_focus"
    mood_data["bpm"] = max(50, min(90, int(mood_data.get("bpm", 62))))
    return mood_data