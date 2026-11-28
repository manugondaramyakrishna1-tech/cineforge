# CineForge Local GPU Bridge
Local inference only; no third-party generation API.

## Requirements
Python 3.10/3.11 and an NVIDIA CUDA GPU with sufficient VRAM. First run downloads CogVideoX-2b weights.

## Setup and run
```bash
python -m pip install -r requirements.txt
export CINEFORGE_MOBILE_TOKEN="use-a-long-random-secret"
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```
Keep the service local or use a secured HTTPS tunnel. Do not expose it publicly without security controls.

## Endpoints
- GET /api/mobile/health (Bearer token)
- POST /api/mobile/render (JSON prompt; Bearer token; asynchronous job)
- GET /api/mobile/jobs/{id} (Bearer token)

Video encoding uses PyAV libraries, not shelling out to FFmpeg. CUDA is required. Output is saved under outputs/. This bridge is a basic inference integration; it has not been tested on a GPU host in this environment.
