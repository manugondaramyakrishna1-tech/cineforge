# CineForge mobile UI

The FastAPI server now serves a mobile-friendly interface at its root URL.

## Start
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
Open `http://YOUR_SERVER:8000/` on a mobile browser. The UI checks `/health`, submits prompts to `/jobs`, polls status, and displays the MP4 when complete.

This requires a CUDA-capable server for generation. If API and UI share the same origin, CORS configuration is not required. For public deployment use HTTPS and add authentication and rate limits before sharing the server.
