
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from urllib.parse import urlparse, parse_qs
import re

app = FastAPI(title="Transcript Service v2")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

class TranscriptResponse(BaseModel):
    source: str
    language: Optional[str] = None
    transcript: str

YOUTUBE_ID_RE = re.compile(r"^[0-9A-Za-z_-]{11}$")

def extract_youtube_id(url: str) -> Optional[str]:
    """
    Supports:
    - https://www.youtube.com/watch?v=VIDEOID
    - https://youtu.be/VIDEOID
    - https://www.youtube.com/shorts/VIDEOID
    - https://www.youtube.com/embed/VIDEOID
    - with extra params (?si=..., &t=, etc.)
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")

        # watch?v=ID
        if "youtube.com" in host:
            qs = parse_qs(parsed.query or "")
            if "v" in qs and qs["v"]:
                cand = qs["v"][0]
                if YOUTUBE_ID_RE.match(cand):
                    return cand
            # shorts/ID, embed/ID
            parts = path.split("/")
            if len(parts) >= 2 and parts[0] in {"shorts", "embed"}:
                cand = parts[1]
                if YOUTUBE_ID_RE.match(cand):
                    return cand
        # youtu.be/ID
        if "youtu.be" in host:
            cand = path.split("/")[0]
            if YOUTUBE_ID_RE.match(cand):
                return cand
    except Exception:
        return None
    return None

@app.get("/", tags=["health"])
def health():
    return {"ok": True, "service": "Transcript Service v2"}

@app.get("/transcript", response_model=TranscriptResponse)
def get_transcript(url: str = Query(..., description="Video URL")):
    vid = extract_youtube_id(url)
    if not vid:
        raise HTTPException(400, "Could not extract a YouTube video ID from URL.")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        segments = YouTubeTranscriptApi.get_transcript(vid)
        if not segments:
            raise HTTPException(404, "Transcript empty or unavailable.")
        text = " ".join([seg.get("text", "") for seg in segments if seg.get("text")])
        lang = segments[0].get("lang", "en") if segments else None
        return {"source": "youtube", "language": lang, "transcript": text}
    except Exception as e:
        raise HTTPException(404, f"Transcript unavailable or video has no captions. {e}")
