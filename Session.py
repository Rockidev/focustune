from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class StudySession(Base):
    __tablename__ = "sessions"

    id             = Column(String, primary_key=True)          # UUID
    user_id        = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # What the user told us
    input_type     = Column(String, nullable=False)            # "describe" | "quick"
    description    = Column(Text, nullable=True)               # freeform text they typed
    vibe           = Column(String, nullable=True)             # quick pick vibe name
    language       = Column(String, default="auto")

    # What Claude detected
    mood_tag       = Column(String, nullable=True, index=True) # "deep_focus" | "exam_crunch" etc.
    detected_bpm   = Column(Integer, nullable=True)
    energy_level   = Column(Float, nullable=True)
    style_keywords = Column(Text, nullable=True)               # JSON list as string

    # What MusicGen received
    music_prompt   = Column(Text, nullable=True)
    final_bpm      = Column(Integer, nullable=True)            # after personalization

    # Output
    audio_path     = Column(String, nullable=True)
    duration_sec   = Column(Integer, default=30)

    created_at     = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user     = relationship("User",     back_populates="sessions")
    feedback = relationship("Feedback", back_populates="session", uselist=False)