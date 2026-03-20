from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./padhai.db")
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── Models ────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"
    id                    = Column(String, primary_key=True)
    google_id             = Column(String, unique=True, nullable=False, index=True)
    email                 = Column(String, unique=True, nullable=False)
    name                  = Column(String, nullable=False)
    avatar_url            = Column(String, nullable=True)
    spotify_access_token  = Column(String, nullable=True)
    spotify_refresh_token = Column(String, nullable=True)
    spotify_token_expiry  = Column(DateTime, nullable=True)
    spotify_taste         = Column(Text, nullable=True)
    created_at            = Column(DateTime, default=datetime.utcnow)
    updated_at            = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    sessions              = relationship("StudySession", back_populates="user")
    feedbacks             = relationship("Feedback", back_populates="user")
    learned_prefs         = relationship("LearnedPrefs", back_populates="user")


class StudySession(Base):
    __tablename__ = "sessions"
    id             = Column(String, primary_key=True)
    user_id        = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    input_type     = Column(String, nullable=False)
    description    = Column(Text, nullable=True)
    vibe           = Column(String, nullable=True)
    language       = Column(String, default="auto")
    mood_tag       = Column(String, nullable=True, index=True)
    detected_bpm   = Column(Integer, nullable=True)
    energy_level   = Column(Float, nullable=True)
    style_keywords = Column(Text, nullable=True)
    music_prompt   = Column(Text, nullable=True)
    final_bpm      = Column(Integer, nullable=True)
    audio_path     = Column(String, nullable=True)
    duration_sec   = Column(Integer, default=30)
    created_at     = Column(DateTime, default=datetime.utcnow)
    user           = relationship("User", back_populates="sessions")
    feedback       = relationship("Feedback", back_populates="session", uselist=False)


class Feedback(Base):
    __tablename__ = "feedback"
    id                  = Column(String, primary_key=True)
    session_id          = Column(String, ForeignKey("sessions.id"), unique=True, index=True)
    user_id             = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    reaction            = Column(String, nullable=False)
    rating              = Column(Integer, nullable=True)
    listen_duration_sec = Column(Integer, default=0)
    created_at          = Column(DateTime, default=datetime.utcnow)
    session             = relationship("StudySession", back_populates="feedback")
    user                = relationship("User", back_populates="feedbacks")


class LearnedPrefs(Base):
    __tablename__ = "learned_prefs"
    id                = Column(String, primary_key=True)
    user_id           = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    mood_tag          = Column(String, nullable=False, index=True)
    preferred_bpm     = Column(Float, nullable=True)
    top_keywords      = Column(Text, nullable=True)
    avoided_keywords  = Column(Text, nullable=True)
    love_rate         = Column(Float, default=0.0)
    skip_rate         = Column(Float, default=0.0)
    avg_listen_sec    = Column(Float, default=0.0)
    sample_count      = Column(Integer, default=0)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user              = relationship("User", back_populates="learned_prefs")


# ── Helpers ───────────────────────────────────────────────

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)