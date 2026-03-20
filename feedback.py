import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from collections import Counter

from Database import get_db, Feedback, StudySession, LearnedPrefs
from schemes import FeedbackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])

REACTION_WEIGHTS = {"loved": 3, "ok": 1, "skip": -1}


def recalculate_prefs(user_id: str, mood_tag: str, db: Session):
    sessions = (
        db.query(StudySession)
        .filter(StudySession.user_id == user_id, StudySession.mood_tag == mood_tag)
        .order_by(StudySession.created_at.desc())
        .limit(20)
        .all()
    )
    if not sessions:
        return

    session_ids = [s.id for s in sessions]
    feedbacks = db.query(Feedback).filter(Feedback.session_id.in_(session_ids)).all()
    feedback_map = {f.session_id: f for f in feedbacks}

    weighted_bpm_sum = 0
    weight_total = 0
    loved_keywords = []
    skipped_keywords = []
    loved_count = 0
    skip_count = 0

    for session in sessions:
        fb = feedback_map.get(session.id)
        if not fb:
            continue
        weight = REACTION_WEIGHTS.get(fb.reaction, 0)
        if session.final_bpm and weight > 0:
            weighted_bpm_sum += session.final_bpm * weight
            weight_total += weight
        if session.style_keywords:
            try:
                keywords = json.loads(session.style_keywords)
            except Exception:
                keywords = []
            if fb.reaction == "loved":
                loved_keywords.extend(keywords)
                loved_count += 1
            elif fb.reaction == "skip":
                skipped_keywords.extend(keywords)
                skip_count += 1

    preferred_bpm = round(weighted_bpm_sum / weight_total, 1) if weight_total > 0 else None
    top_keywords  = [kw for kw, _ in Counter(loved_keywords).most_common(5)]
    avoided_kw    = [kw for kw, _ in Counter(skipped_keywords).most_common(3)]

    total = loved_count + skip_count
    love_rate = loved_count / total if total else 0.0
    skip_rate = skip_count  / total if total else 0.0

    prefs = (
        db.query(LearnedPrefs)
        .filter(LearnedPrefs.user_id == user_id, LearnedPrefs.mood_tag == mood_tag)
        .first()
    )
    if prefs:
        prefs.preferred_bpm    = preferred_bpm
        prefs.top_keywords     = json.dumps(top_keywords)
        prefs.avoided_keywords = json.dumps(avoided_kw)
        prefs.love_rate        = round(love_rate, 3)
        prefs.skip_rate        = round(skip_rate, 3)
        prefs.sample_count     = len(sessions)
    else:
        prefs = LearnedPrefs(
            id=str(uuid.uuid4()),
            user_id=user_id,
            mood_tag=mood_tag,
            preferred_bpm=preferred_bpm,
            top_keywords=json.dumps(top_keywords),
            avoided_keywords=json.dumps(avoided_kw),
            love_rate=round(love_rate, 3),
            skip_rate=round(skip_rate, 3),
            sample_count=len(sessions),
        )
        db.add(prefs)
    db.commit()


@router.post("/")
async def submit_feedback(
    req: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if req.reaction not in ("loved", "ok", "skip"):
        raise HTTPException(status_code=400, detail="reaction must be loved | ok | skip")

    session = db.query(StudySession).filter(StudySession.id == req.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    existing = db.query(Feedback).filter(Feedback.session_id == req.session_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Feedback already submitted")

    feedback = Feedback(
        id=str(uuid.uuid4()),
        session_id=req.session_id,
        user_id=session.user_id,
        reaction=req.reaction,
        rating=req.rating,
        listen_duration_sec=req.listen_duration_sec,
    )
    db.add(feedback)
    db.commit()

    if session.mood_tag:
        background_tasks.add_task(recalculate_prefs, session.user_id, session.mood_tag, db)

    return {
        "status": "saved",
        "message": "Your feedback is training your personal music model",
        "reaction": req.reaction,
    }