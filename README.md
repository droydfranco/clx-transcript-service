# CLX Transcript Service (v5)

- Tries YouTube captions first (manual/auto, preferred languages)
- Optional STT fallback (OpenAI Whisper or AssemblyAI) when captions are unavailable
- Endpoints:
  - `/` health
  - `/transcript?url=...&languages=en,fil&fallback_stt=true`
  - `/auto_transcript?url=...&languages=en` (auto captions→STT)

## Env vars (for STT)
- `OPENAI_API_KEY` (for Whisper) or `ASSEMBLYAI_API_KEY`

## Run locally
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
