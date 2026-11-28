# GPU runtime setup

CineForge requires an NVIDIA CUDA GPU for practical local text-to-video inference.

## Check runtime
```bash
python -c "import torch; print('CUDA:',torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'No CUDA GPU')"
```

## Setup checklist
- Select an NVIDIA GPU instance in your cloud environment.
- Install PyTorch with a CUDA build compatible with the host drivers, using the official PyTorch install selector.
- Install project dependencies with `pip install -r requirements.txt`.
- Restart the runtime/kernel.
- Run the check above before launching the app.

## Security and cost
Use trusted cloud providers, never commit tokens or credentials, and shut down GPU instances when finished. GPU usage may incur charges; review provider pricing before starting.
