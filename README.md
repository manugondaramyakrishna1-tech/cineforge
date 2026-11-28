# CineForge — Cloud GPU Model Pipeline

Python text-to-video generation with PyTorch, Hugging Face Diffusers and CogVideoX-2B.

## Free GPU mode
See [FREE_GPU_MODE.md](FREE_GPU_MODE.md) and [free_gpu_notebook.py](free_gpu_notebook.py) for manual notebook-based generation on free GPU sessions where available. These sessions are temporary and do not provide a persistent public API.

## GPU verification
`python -c "import torch; print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'GPU not detected')"`

Default model: `THUDM/CogVideoX-2b`. Review the model card and license before use. No Actions workflow is added or triggered.
