# Queue manager

CineForge uses a single-worker executor to serialize generation on a single GPU.

- `GET /queue`: reports running job and queue size/positions.
- `DELETE /jobs/{job_id}`: cancels a queued job if it has not started. Running jobs cannot be cancelled through this endpoint.
- The mobile job-history view displays queue positions and offers cancellation for queued jobs.

Jobs are persisted to SQLite. The queue itself is process-local: after a server restart, pending jobs are marked interrupted rather than automatically resumed. This prototype is not a multi-host distributed queue.
