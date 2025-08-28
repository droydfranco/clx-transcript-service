# CLX Transcript Service (v2)

Improved URL parsing and a health endpoint.

## Run locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints
- `/` -> health check
- `/transcript?url=VIDEO_URL` -> returns transcript JSON (if captions exist)
