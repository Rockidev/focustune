from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = "users"

    id               = Column(String, primary_key=True)        # UUID
    google_id        = Column(String, unique=True, nullable=False, index=True)
    email            = Column(String, unique=True, nullable=False)
    name             = Column(String, nullable=False)
    avatar_url       = Column(String, nullable=True)

    # Spotify fields — null until user connects Spotify
    spotify_access_token  = Column(String, nullable=True)
    spotify_refresh_token = Column(String, nullable=True)
    spotify_token_expiry  = Column(DateTime, nullable=True)
    spotify_taste         = Column(Text, nullable=True)        # JSON string

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions      = relationship("StudySession",  back_populates="user")
    feedbacks     = relationship("Feedback",       back_populates="user")
    learned_prefs = relationship("LearnedPrefs",   back_populates="user")