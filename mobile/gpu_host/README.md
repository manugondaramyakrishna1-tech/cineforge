# CineForge GPU Host Bridge

This API is a lightweight bridge for the Android companion app.

## Run
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000

## Endpoints
- GET /api/mobile/health
- POST /api/mobile/render (placeholder; inference not wired)

This scaffold does not generate video. Keep the host private and use HTTPS/authentication before exposing it to a network.
