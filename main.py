
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from urllib.parse import urlparse, parse_qs
import re

app = FastAPI(title="Transcript Service v3")
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
    """Handle watch, youtu.be, shorts, embed; ignore extra params."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")

        if "youtube.com" in host:
            qs = parse_qs(parsed.query or "")
            if "v" in qs and qs["v"]:
                cand = qs["v"][0]
                if YOUTUBE_ID_RE.match(cand):
                    return cand
            parts = path.split("/")
            if len(parts) >= 2 and parts[0] in {"shorts", "embed"}:
                cand = parts[1]
                if YOUTUBE_ID_RE.match(cand):
                    return cand
        if "youtu.be" in host:
            cand = path.split("/")[0]
            if YOUTUBE_ID_RE.match(cand):
                return cand
    except Exception:
        return None
    return None

@app.get("/", tags=["health"])
def health():
    return {"ok": True, "service": "Transcript Service v3"}

@app.get("/transcript", response_model=TranscriptResponse)
def get_transcript(
    url: str = Query(..., description="Video URL"),
    languages: Optional[str] = Query(None, description="Comma-separated language codes, e.g., en,es,fil")
):
    vid = extract_youtube_id(url)
    if not vid:
        raise HTTPException(400, "Could not extract a YouTube video ID from URL.")
    lang_list: List[str] = []
    if languages:
        lang_list = [c.strip() for c in languages.split(",") if c.strip()]

    try:
        from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, NoTranscriptAvailable
        # Prefer list_transcripts to handle manually-created vs auto-generated
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(vid)
        except Exception as e:
            raise HTTPException(404, f"Transcript list unavailable: {e}")

        # Try order of preference:
        # 1) manually created in preferred languages
        # 2) auto-generated in preferred languages
        # 3) any manually created
        # 4) any auto-generated
        def fetch_or_none(getter):
            try:
                t = getter()
                return t.fetch(), t.language_code
            except Exception:
                return None, None

        prefs = lang_list if lang_list else ["en"]
        # 1
        for l in prefs:
            data, code = fetch_or_none(lambda l=l: transcript_list.find_manually_created_transcript([l]))
            if data: 
                text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                return {"source": "youtube", "language": code, "transcript": text}
        # 2
        for l in prefs:
            data, code = fetch_or_none(lambda l=l: transcript_list.find_generated_transcript([l]))
            if data: 
                text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                return {"source": "youtube", "language": code, "transcript": text}
        # 3 - any manual
        try:
            any_manual = [t for t in transcript_list if getattr(t, 'is_generated', False) is False]
            if any_manual:
                data = any_manual[0].fetch()
                code = any_manual[0].language_code
                text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                return {"source": "youtube", "language": code, "transcript": text}
        except Exception:
            pass
        # 4 - any auto
        try:
            any_auto = [t for t in transcript_list if getattr(t, 'is_generated', False) is True]
            if any_auto:
                data = any_auto[0].fetch()
                code = any_auto[0].language_code
                text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                return {"source": "youtube", "language": code, "transcript": text}
        except Exception:
            pass

        raise HTTPException(404, "No transcripts available for this video (captions disabled).")
    except TranscriptsDisabled:
        raise HTTPException(404, "Transcripts are disabled for this video.")
    except NoTranscriptFound:
        raise HTTPException(404, "No transcript found for the requested languages.")
    except NoTranscriptAvailable:
        raise HTTPException(404, "No transcript available for this video.")
    except Exception as e:
        raise HTTPException(500, f"Unexpected error: {e}")
