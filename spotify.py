import httpx
import os
from datetime import datetime
from urllib.parse import urlencode

SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI  = os.getenv("SPOTIFY_REDIRECT_URI")
SCOPES   = "user-top-read user-read-recently-played user-library-read"
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL= "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


def get_auth_url() -> str:
    params = {
        "client_id":     SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri":  SPOTIFY_REDIRECT_URI,
        "scope":         SCOPES,
        "show_dialog":   "false",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type":  "authorization_code",
                "code":         code,
                "redirect_uri": SPOTIFY_REDIRECT_URI,
            },
            auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        )
        resp.raise_for_status()
        return resp.json()


async def get_spotify_taste(access_token: str) -> dict:
    """
    Read user's top tracks audio features + top genres.
    Used only as preference signals — no audio stored, no model training.
    Fully compliant with Spotify ToS.
    """
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        top_tracks_resp = await client.get(
            f"{API_BASE}/me/top/tracks",
            headers=headers,
            params={"limit": 20, "time_range": "medium_term"},
        )
        top_tracks_resp.raise_for_status()
        tracks = top_tracks_resp.json().get("items", [])
        if not tracks:
            return _default_taste()

        track_ids = [t["id"] for t in tracks]
        features_resp = await client.get(
            f"{API_BASE}/audio-features",
            headers=headers,
            params={"ids": ",".join(track_ids)},
        )
        features_resp.raise_for_status()
        features_list = [f for f in features_resp.json().get("audio_features", []) if f]

        top_artists_resp = await client.get(
            f"{API_BASE}/me/top/artists",
            headers=headers,
            params={"limit": 5, "time_range": "medium_term"},
        )
        top_artists_resp.raise_for_status()
        artists = top_artists_resp.json().get("items", [])

    def avg(key):
        vals = [f[key] for f in features_list if key in f and f[key] is not None]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    all_genres = []
    for artist in artists:
        all_genres.extend(artist.get("genres", []))
    genre_counts = {}
    for g in all_genres:
        genre_counts[g] = genre_counts.get(g, 0) + 1
    top_genres = sorted(genre_counts, key=genre_counts.get, reverse=True)[:3]

    return {
        "avg_bpm":          round(avg("tempo")),
        "energy":           avg("energy"),
        "instrumentalness": avg("instrumentalness"),
        "acousticness":     avg("acousticness"),
        "valence":          avg("valence"),
        "danceability":     avg("danceability"),
        "top_genres":       top_genres,
        "connected":        True,
        "fetched_at":       datetime.utcnow().isoformat(),
    }


def _default_taste() -> dict:
    return {
        "avg_bpm": 70, "energy": 0.5, "instrumentalness": 0.4,
        "acousticness": 0.4, "valence": 0.5, "danceability": 0.5,
        "top_genres": [], "connected": False,
        "fetched_at": datetime.utcnow().isoformat(),
    }