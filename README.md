# CLX Transcript Service

A simple FastAPI service that fetches YouTube video transcripts and returns them as plain text.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoint

- `/transcript?url=VIDEO_URL`
  - Returns transcript text if available
