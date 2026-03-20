import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from Database import get_db, User, StudySession, Feedback, LearnedPrefs
from schemes import ProfileOut, UserOut, SpotifyTasteOut, PrefOut

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user found — log in first")

    sessions  = db.query(StudySession).filter(StudySession.user_id == user.id).all()
    feedbacks = db.query(Feedback).filter(Feedback.user_id == user.id).all()

    total_sessions     = len(sessions)
    total_listen_sec   = sum(f.listen_duration_sec or 0 for f in feedbacks)
    total_listen_hours = round(total_listen_sec / 3600, 1)
    loved              = sum(1 for f in feedbacks if f.reaction == "loved")
    overall_love_rate  = round(loved / len(feedbacks), 2) if feedbacks else 0.0

    spotify_taste_out = None
    if user.spotify_taste:
        try:
            taste = json.loads(user.spotify_taste)
            spotify_taste_out = SpotifyTasteOut(
                avg_bpm=taste.get("avg_bpm", 70),
                energy=taste.get("energy", 0.5),
                instrumentalness=taste.get("instrumentalness", 0.4),
                acousticness=taste.get("acousticness", 0.4),
                valence=taste.get("valence", 0.5),
                top_genres=taste.get("top_genres", []),
                connected=True,
            )
        except Exception:
            pass

    all_prefs = (
        db.query(LearnedPrefs)
        .filter(LearnedPrefs.user_id == user.id)
        .order_by(LearnedPrefs.sample_count.desc())
        .all()
    )
    prefs_out = [
        PrefOut(
            mood_tag=p.mood_tag,
            preferred_bpm=p.preferred_bpm,
            top_keywords=json.loads(p.top_keywords or "[]"),
            love_rate=p.love_rate,
            skip_rate=p.skip_rate,
            sample_count=p.sample_count,
        )
        for p in all_prefs
    ]

    return ProfileOut(
        user=UserOut(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            spotify_connected=user.spotify_taste is not None,
            created_at=user.created_at,
        ),
        total_sessions=total_sessions,
        total_listen_hours=total_listen_hours,
        overall_love_rate=overall_love_rate,
        spotify_taste=spotify_taste_out,
        learned_prefs=prefs_out,
    )