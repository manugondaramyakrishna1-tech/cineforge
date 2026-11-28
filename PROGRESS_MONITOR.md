# Progress and monitoring

- `GET /monitor`: combined GPU telemetry, queue snapshot and active job details.
- GPU telemetry is queried via `nvidia-smi`; it is optional and unavailable on CPU-only hosts.
- Active jobs report stage, progress percentage, elapsed time and status.
- The model pipeline reports inference-step progress through Diffusers callbacks. Loading and export phases may not have fine-grained progress.
- Mobile UI displays job progress and available GPU utilization/VRAM telemetry.

Progress percentage reflects denoising inference steps and may not represent the entire end-to-end duration. No GPU is provisioned by this code.
