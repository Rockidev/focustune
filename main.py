from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from Database import create_tables
import Auth
import music_routes
import feedback
import Profile

create_tables()
os.makedirs(os.getenv("MUSIC_OUTPUT_DIR", "./audio_output"), exist_ok=True)

app = FastAPI(
    title="PadhaiBeats API",
    description="AI study music for Indian students",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
        "https://ubiquitous-platypus-147a73.netlify.app",
        "https://69c021d5fd19e248d18ecde8--ubiquitous-platypus-147a73.netlify.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(Auth.router)
app.include_router(music_routes.router)
app.include_router(feedback.router)
app.include_router(Profile.router)


@app.get("/")
def root():
    return {
        "app": "PadhaiBeats API",
        "status": "running",
        "docs": "/docs",
    }

@app.get("/health")
def health():
    return {"status": "ok"}