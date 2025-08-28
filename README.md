# CLX Transcript Service (v3)

- Robust YouTube ID parsing (watch / youtu.be / shorts / embed)
- Health endpoint at `/`
- Better transcript retrieval using `list_transcripts()`
- Pinned youtube-transcript-api==0.6.2

## Run locally
```
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints
- `/` -> health check
- `/transcript?url=VIDEO_URL&languages=en,fil` -> returns transcript JSON (if captions exist)
