from sqlalchemy import Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class LearnedPrefs(Base):
    __tablename__ = "learned_prefs"

    id              = Column(String, primary_key=True)
    user_id         = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    mood_tag        = Column(String, nullable=False, index=True)  # one row per mood per user

    # Learned from feedback history
    preferred_bpm   = Column(Float, nullable=True)       # weighted average
    top_keywords    = Column(Text, nullable=True)         # JSON list — most loved style words
    avoided_keywords = Column(Text, nullable=True)        # JSON list — most skipped style words

    # Rates
    love_rate       = Column(Float, default=0.0)          # 0.0 to 1.0
    skip_rate       = Column(Float, default=0.0)
    avg_listen_sec  = Column(Float, default=0.0)

    # How much data we have — drives cold start logic
    sample_count    = Column(Integer, default=0)
    # 0-3 sessions = cold (use defaults)
    # 4-9 sessions = warming (blend defaults + learned)
    # 10+ sessions = warm (full personalization)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="learned_prefs")