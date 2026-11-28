# CineForge FastAPI job API

The API accepts a prompt, returns a job ID immediately, and lets a mobile client poll job status.

## Run
Install dependencies:
```bash
pip install -r requirements.txt
```
Start the API from the repository root:
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
Swagger UI: http://localhost:8000/docs

## Endpoints
- `GET /health`: runtime/GPU availability
- `POST /jobs`: submit a generation job (HTTP 202)
- `GET /jobs/{job_id}`: poll status
- `GET /jobs/{job_id}/video`: download completed MP4

## Submit example
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"prompt":"A peaceful futuristic city at sunrise","frames":25,"steps":25,"seed":42}'
```
Response:
```json
{"job_id":"...","status":"queued","status_url":"/jobs/..."}
```

Poll:
```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID
```
Statuses are `queued`, `running`, `completed`, or `failed`. When completed, the response includes `download_url`.

## Mobile client integration
1. POST the JSON prompt to `/jobs`.
2. Store the returned `job_id`.
3. Poll `/jobs/{job_id}` periodically until completed or failed.
4. Download from `/jobs/{job_id}/video` when completed.

**Prototype limitations:** job state is in memory and disappears on restart; one worker is used to avoid concurrent GPU model loading. Do not expose this server publicly without authentication, request limits, HTTPS, and an appropriate deployment configuration.
