import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
import jwt
import os

from Database import get_db, User, StudySession, LearnedPrefs
from schemes import DescribeRequest, QuickRequest, MoodResponse
from claude import analyze_description
from music import mood_to_musicgen_prompt, get_preset, generate_audio

router = APIRouter(prefix="/music", tags=["music"])

JWT_SECRET    = os.getenv("JWT_SECRET", "focustune-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get logged in user from JWT token. Returns None if not logged in."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


def _get_learned_prefs_dict(db, user_id, mood_tag):
    prefs = (
        db.query(LearnedPrefs)
        .filter(LearnedPrefs.user_id == user_id, LearnedPrefs.mood_tag == mood_tag)
        .first()
    )
    if not prefs or prefs.sample_count < 3:
        return None
    return {
        "preferred_bpm":    prefs.preferred_bpm,
        "top_keywords":     json.loads(prefs.top_keywords or "[]"),
        "avoided_keywords": json.loads(prefs.avoided_keywords or "[]"),
        "love_rate":        prefs.love_rate,
        "skip_rate":        prefs.skip_rate,
        "sample_count":     prefs.sample_count,
    }


def _get_spotify_taste(user):
    if not user or not user.spotify_taste:
        return None
    try:
        return json.loads(user.spotify_taste)
    except Exception:
        return None


@router.post("/describe", response_model=MoodResponse)
async def describe_to_music(
    req: DescribeRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user = get_current_user(authorization, db)
    spotify_taste = _get_spotify_taste(user)

    mood_data = await analyze_description(
        description=req.description,
        language=req.language,
        spotify_taste=spotify_taste,
        learned_prefs=_get_learned_prefs_dict(db, user.id, "unknown") if user else None,
    )

    music_prompt = mood_to_musicgen_prompt(
        mood_tag=mood_data["mood_tag"],
        bpm=mood_data["bpm"],
        style_keywords=mood_data["style_keywords"],
        spotify_taste=spotify_taste,
    )

    audio_path = await generate_audio(music_prompt, duration=req.duration)

    session_id = str(uuid.uuid4())
    session = StudySession(
        id=session_id,
        user_id=user.id if user else "guest",
        input_type="describe",
        description=req.description,
        language=req.language,
        mood_tag=mood_data["mood_tag"],
        detected_bpm=mood_data["bpm"],
        energy_level=mood_data.get("energy_level"),
        style_keywords=json.dumps(mood_data["style_keywords"]),
        music_prompt=music_prompt,
        final_bpm=mood_data["bpm"],
        audio_path=audio_path,
        duration_sec=req.duration,
    )
    db.add(session)
    db.commit()

    return MoodResponse(
        mood_tag=mood_data["mood_tag"],
        bpm=mood_data["bpm"],
        energy_level=mood_data.get("energy_level", 0.5),
        style_keywords=mood_data["style_keywords"],
        music_prompt=music_prompt,
        session_id=session_id,
    )


@router.post("/quick", response_model=MoodResponse)
async def quick_music(
    req: QuickRequest,
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    user = get_current_user(authorization, db)
    spotify_taste = _get_spotify_taste(user)
    preset = get_preset(req.vibe, spotify_taste=spotify_taste)

    audio_path = await generate_audio(preset["music_prompt"], duration=req.duration)

    session_id = str(uuid.uuid4())
    session = StudySession(
        id=session_id,
        user_id=user.id if user else "guest",
        input_type="quick",
        vibe=req.vibe,
        mood_tag=preset["mood_tag"],
        detected_bpm=preset["bpm"],
        energy_level=preset["energy_level"],
        style_keywords=json.dumps(preset["style_keywords"]),
        music_prompt=preset["music_prompt"],
        final_bpm=preset["bpm"],
        audio_path=audio_path,
        duration_sec=req.duration,
    )
    db.add(session)
    db.commit()

    return MoodResponse(
        mood_tag=preset["mood_tag"],
        bpm=preset["bpm"],
        energy_level=preset["energy_level"],
        style_keywords=preset["style_keywords"],
        music_prompt=preset["music_prompt"],
        session_id=session_id,
    )


@router.get("/audio/{session_id}")
def get_audio(session_id: str, db: Session = Depends(get_db)):
    session = db.query(StudySession).filter(StudySession.id == session_id).first()
    if not session or not session.audio_path:
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(
        session.audio_path,
        media_type="audio/wav",
        filename="padhai_beats.wav",
    )