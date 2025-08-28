from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import re

app = FastAPI(title="Transcript Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

class TranscriptResponse(BaseModel):
    source: str
    language: Optional[str] = None
    transcript: str

YOUTUBE_ID_RE = re.compile(r"(?:v=|/)([0-9A-Za-z_-]{11}).*")

def extract_yt_id(url: str) -> Optional[str]:
    m = YOUTUBE_ID_RE.search(url)
    return m.group(1) if m else None

@app.get("/transcript", response_model=TranscriptResponse)
def get_transcript(url: str = Query(..., description="Video URL")):
    # Extract YouTube ID
    vid = extract_yt_id(url)
    if not vid:
        raise HTTPException(400, "Could not extract a YouTube video ID from URL.")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        s = YouTubeTranscriptApi.get_transcript(vid)
        text = " ".join([seg["text"] for seg in s if seg.get("text")])
        return {"source": "youtube", "language": s[0].get("lang", "en") if s else None, "transcript": text}
    except Exception as e:
        raise HTTPException(404, f"Transcript unavailable or video has no captions. {e}")
