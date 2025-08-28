
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from urllib.parse import urlparse, parse_qs
import os, re

app = FastAPI(title="Transcript Service v4")
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
    return {"ok": True, "service": "Transcript Service v4"}

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
    else:
        lang_list = ["en"]

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        # Attempt robust method 1: list_transcripts (handles manual/auto)
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(vid)
            # prefer manual in requested languages
            for l in lang_list:
                try:
                    t = transcript_list.find_manually_created_transcript([l])
                    data = t.fetch()
                    text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                    return {"source": "youtube", "language": t.language_code, "transcript": text}
                except Exception:
                    pass
            # prefer auto in requested languages
            for l in lang_list:
                try:
                    t = transcript_list.find_generated_transcript([l])
                    data = t.fetch()
                    text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                    return {"source": "youtube", "language": t.language_code, "transcript": text}
                except Exception:
                    pass
            # any manual
            manuals = [t for t in transcript_list if getattr(t, 'is_generated', False) is False]
            if manuals:
                data = manuals[0].fetch()
                text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                return {"source": "youtube", "language": manuals[0].language_code, "transcript": text}
            # any auto
            autos = [t for t in transcript_list if getattr(t, 'is_generated', False) is True]
            if autos:
                data = autos[0].fetch()
                text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                return {"source": "youtube", "language": autos[0].language_code, "transcript": text}
        except Exception as e_list:
            # Fall back to simple API call (some videos work here even if list_transcripts fails).
            try:
                data = YouTubeTranscriptApi.get_transcript(vid, languages=lang_list)
                text = " ".join(seg.get("text","") for seg in data if seg.get("text"))
                # Try to guess a language code if not present:
                lang = None
                if isinstance(data, list) and data:
                    lang = data[0].get("language", None) or data[0].get("lang", None)
                return {"source": "youtube", "language": lang or (lang_list[0] if lang_list else None), "transcript": text}
            except Exception as e_simple:
                raise HTTPException(404, f"No transcripts available (list error: {e_list}; simple error: {e_simple}).")

        raise HTTPException(404, "No transcripts available for this video (captions disabled).")
    except Exception as e:
        raise HTTPException(500, f"Unexpected error: {e}")
