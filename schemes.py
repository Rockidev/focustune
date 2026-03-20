from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    avatar_url: Optional[str] = None
    spotify_connected: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DescribeRequest(BaseModel):
    description: str
    language: str = "auto"
    duration: int = 30


class QuickRequest(BaseModel):
    vibe: str
    duration: int = 30


class MoodResponse(BaseModel):
    mood_tag: str
    bpm: int
    energy_level: float
    style_keywords: List[str]
    music_prompt: str
    session_id: str


class FeedbackRequest(BaseModel):
    session_id: str
    reaction: str
    rating: Optional[int] = None
    listen_duration_sec: int = 0


class SpotifyTasteOut(BaseModel):
    avg_bpm: float
    energy: float
    instrumentalness: float
    acousticness: float
    valence: float
    top_genres: List[str]
    connected: bool


class PrefOut(BaseModel):
    mood_tag: str
    preferred_bpm: Optional[float] = None
    top_keywords: List[str]
    love_rate: float
    skip_rate: float
    sample_count: int


class ProfileOut(BaseModel):
    user: UserOut
    total_sessions: int
    total_listen_hours: float
    overall_love_rate: float
    spotify_taste: Optional[SpotifyTasteOut] = None
    learned_prefs: List[PrefOut]