# Persistent job history

CineForge API v1.3 stores generation job metadata in `cineforge_jobs.sqlite3` beside the API process. Generated MP4s are stored in `outputs/`.

- `GET /jobs`: recent history (up to 200 records; default 50)
- `GET /jobs/{job_id}`: status and job details
- `GET /jobs/{job_id}/video`: download completed output

History includes prompt, status, timestamps, settings and error text. The database does not store video contents. Keep the SQLite file and outputs directory on persistent storage if deploying to a host that resets its filesystem.

On startup, queued or running jobs from a prior process are marked failed as interrupted; the service does not automatically retry generation. Job records and videos are not automatically pruned.

This prototype has no authentication. Do not expose it publicly without adding authentication, rate limits and storage protections.
