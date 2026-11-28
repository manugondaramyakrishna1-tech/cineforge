# GPU runtime connection checklist

CineForge executes inference on the host where its API runs. A mobile client does not provide or attach GPU hardware.

## Diagnostic
Use the health endpoint or run:
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'GPU unavailable')"
```
The health endpoint now includes device count and, when CUDA is unavailable, an explanatory hint plus a bounded `nvidia-smi` diagnostic (if the command exists).

## Host requirements
- NVIDIA GPU hardware exposed to the host/container.
- NVIDIA driver installed on host and compatible with the CUDA-enabled PyTorch package.
- GPU passthrough configured by the container/runtime provider.
- Install project dependencies and start: `uvicorn api:app --host 0.0.0.0 --port 8000`.

No application code can install, attach or provision physical GPU hardware in a GPU-less environment.

## API behavior
- `GET /health`: GPU status, CUDA build, device count and diagnostics.
- `POST /jobs`: returns 503 if CUDA is not available at submission.
- Mobile UI includes a refresh button to re-check the runtime.

## Security / limitations
Prototype job records are in-memory, so restarting the server loses job state. Add authentication, quota limits, secure file handling and persistent storage before public deployment.
