# CineForge — Cloud GPU Model Pipeline

Python text-to-video generation with **PyTorch + Hugging Face Diffusers + CogVideoX-2B**.

## GPU runtime
Run this on a cloud machine/runtime with an NVIDIA CUDA GPU. A CUDA-enabled PyTorch installation must match the host's CUDA drivers; install PyTorch using the official selector before the remaining dependencies.

Verify GPU:
```bash
python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'GPU not detected')"
```

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
# Windows: .venv\\Scripts\\activate
# Install CUDA-enabled PyTorch first, using the official PyTorch installation selector.
pip install -r requirements.txt
streamlit run app.py
```

Open the Streamlit URL in the cloud runtime. Model weights download on first run.

## CLI
```bash
python model_pipeline.py "A cinematic aerial view of a coastal city at sunset" --output outputs/demo.mp4
```

Default model: `THUDM/CogVideoX-2b`. GPU memory requirements vary by settings and optimizations. Model CPU offload and VAE tiling/slicing are enabled to reduce VRAM use, at a speed cost. Review the model card and license before use.

## Files
- `app.py`: Streamlit UI
- `model_pipeline.py`: reusable inference entrypoint
- `requirements.txt`: Python dependencies

No Actions workflow is added or triggered.
