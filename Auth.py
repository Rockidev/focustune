import uuid
import os
import httpx
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from jose import jwt
from dotenv import load_dotenv

load_dotenv()

from Database import get_db, User
from spotify import get_auth_url, exchange_code_for_token, get_spotify_taste
import json

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
JWT_SECRET           = os.getenv("JWT_SECRET", "focustune-dev-secret-change-in-production")
JWT_ALGORITHM        = "HS256"
JWT_EXPIRE_MINUTES   = 10080
FRONTEND_URL         = os.getenv("FRONTEND_URL", "http://localhost:3000")


def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user_id(token: str) -> str:
    """Decode JWT and return user_id. Raises if invalid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload["sub"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ── Google OAuth ──────────────────────────────────────────

@router.get("/google")
def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_CLIENT_ID not set in .env — add it and restart uvicorn"
        )
    from urllib.parse import urlencode
    params = urlencode({
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "offline",
        "prompt":        "select_account",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code":          code,
                "client_id":     GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri":  GOOGLE_REDIRECT_URI,
                "grant_type":    "authorization_code",
            },
        )
        token_resp.raise_for_status()
        tokens = token_resp.json()

        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    user = db.query(User).filter(User.google_id == userinfo["id"]).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            google_id=userinfo["id"],
            email=userinfo["email"],
            name=userinfo.get("name", "Student"),
            avatar_url=userinfo.get("picture"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_jwt(user.id)
    return RedirectResponse(f"{FRONTEND_URL}/auth/callback?token={token}")


# ── Spotify OAuth ─────────────────────────────────────────

@router.get("/spotify")
def spotify_connect():
    return RedirectResponse(get_auth_url())


@router.get("/spotify/callback")
async def spotify_callback(code: str, db: Session = Depends(get_db)):
    token_data = await exchange_code_for_token(code)
    access_token  = token_data["access_token"]
    refresh_token = token_data.get("refresh_token")
    expires_in    = token_data.get("expires_in", 3600)
    expiry        = datetime.utcnow() + timedelta(seconds=expires_in)

    taste = await get_spotify_taste(access_token)

    # NOTE: In production attach this to the logged-in user via JWT cookie
    # For now we update the first user found (dev mode)
    user = db.query(User).first()
    if user:
        user.spotify_access_token  = access_token
        user.spotify_refresh_token = refresh_token
        user.spotify_token_expiry  = expiry
        user.spotify_taste         = json.dumps(taste)
        db.commit()

    return RedirectResponse(f"{FRONTEND_URL}/settings?spotify=connected")