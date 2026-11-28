# CineForge Free GPU Bridge setup

This bridge lets a temporary Kaggle/Colab GPU notebook poll a reachable CineForge FastAPI server. The notebook makes outbound HTTPS requests, so it does not need a public inbound port.

## 1. Run/deploy the CineForge API
Deploy the repository API on a reachable HTTPS Python host, or run it locally for development:
```bash
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000
```
The API host itself does not need a GPU in bridge mode. It must keep its SQLite database and `outputs/` directory persistent. A temporary/sleeping host can interrupt jobs.

## 2. Configure bridge secret on API host
Create a long random secret and set it as environment variable `CINEFORGE_FREE_GPU_BRIDGE_TOKEN`. Never put this value in mobile UI, source control, or a public notebook. Restart the API after setting it.

Check `GET /health`; it should report `free_gpu_bridge_enabled: true`.

## 3. Start GPU notebook worker
Open a Kaggle notebook and enable GPU if available. Upload/run `free_gpu_bridge_worker.py` after setting these notebook environment variables/secrets:
- `CINEFORGE_API_URL`: base HTTPS URL of your CineForge API (no trailing slash).
- `CINEFORGE_FREE_GPU_BRIDGE_TOKEN`: same secret configured on API host.

Install dependencies in the notebook environment as needed:
```bash
pip install -U diffusers transformers accelerate safetensors imageio imageio-ffmpeg requests
```
Run the worker script and leave the cell running. It loads CogVideoX-2B once, polls for jobs, generates video, and uploads MP4 to CineForge.

## 4. Submit a job
Use the existing mobile UI or API:
```bash
curl -X POST "$CINEFORGE_API_URL/jobs" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A cinematic wide shot of a quiet futuristic city at sunrise","frames":25,"steps":25,"guidance":6.0,"seed":42}'
``
Poll `GET /jobs/{job_id}` and download from `GET /jobs/{job_id}/video` when completed.

## Security and operational notes
- Protect the public API's job-creation endpoints with user authentication/rate limits before public launch. The bridge token authenticates only notebook bridge routes.
- Use HTTPS. Treat the bridge token as a password and rotate it if exposed.
- Notebook disconnects, quota limits, model download time, and GPU availability can interrupt work. Restart the worker to resume polling.
- API server must persist SQLite and output files. For multiple API instances, use shared durable storage and a proper queue; this prototype is single-instance.
- This is free-tier experimentation, not guaranteed free or always-on hosting. Provider GPU access and quotas vary.
- Maximum uploaded video size is currently 500 MB.


## Milestone 15: verify the bridge before using a GPU session

Run these checks from the project root in a Python environment that has the project dependencies installed:

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The tests use a temporary SQLite database and a test-only bridge token. They cover:
- bridge token rejection and authenticated worker heartbeat;
- queued-job claiming;
- MP4 upload completion and video download;
- rejection of non-MP4 upload data;
- worker failure reporting.

These tests do not load CogVideoX or require a GPU. A successful test run verifies the API contract only; a real Kaggle/Colab generation still needs a separate live GPU test.

For a live notebook session, set `CINEFORGE_API_URL` and `CINEFORGE_FREE_GPU_BRIDGE_TOKEN` as notebook secrets. Keep the token private and do not commit it to GitHub.
