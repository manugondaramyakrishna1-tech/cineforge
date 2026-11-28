# GPU runtime connection checklist

CineForge runs generation on the machine where `api.py` is running. A mobile client can call that API over HTTPS, but it does not supply GPU hardware.

## Verify on the actual server
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'GPU unavailable')"
```

## Host requirements
- NVIDIA GPU hardware exposed to the host/container.
- NVIDIA driver installed on the host.
- CUDA-enabled PyTorch wheel compatible with the host driver.
- Install the remaining dependencies from requirements.txt.
- Start the API on the GPU host: `uvicorn api:app --host 0.0.0.0 --port 8000`.

Container deployments need GPU passthrough configured by their host administrator. A container/Codespace without GPU passthrough cannot gain GPU access from application code.

## API behavior
- `GET /health` reports CUDA status, build version and memory info when available.
- `POST /jobs` returns HTTP 503 when CUDA is unavailable, avoiding a queued job that cannot run.
- When available, generation is executed on the server's GPU.

## Mobile connectivity and security
Use the server's HTTPS URL in your mobile app. Never expose an unauthenticated generation API to the public internet. Add authentication, request throttling, quota limits, persistent job storage and secure file handling before public deployment. The prototype job store is process-memory only.
