# CineForge AI — cinematic video creation

CineForge is a Python Streamlit studio for prompt-to-storyboard planning, scene editing, **self-hosted AI scene generation**, narration, timeline assembly and MP4 export. It does **not** invoke the FFmpeg executable.

## Requirements
- Python 3.10+
- Core studio: install `requirements.txt`
- Local AI video generation: a compatible NVIDIA CUDA GPU (recommended) or Apple Silicon device, plus the optional dependencies in `requirements-local-video.txt`
- The default local model is `THUDM/CogVideoX-2b`. Model weights are large and are downloaded to the local Hugging Face cache on first inference.

## Run
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## GPU diagnostic helper (included in Python project)

Run this from the repository root:

```bash
python -m cineforge.gpu_setup
```

The helper checks for the NVIDIA driver tool and PyTorch CUDA detection, then reports the next steps. It does not install NVIDIA drivers or provision physical GPU hardware. If an NVIDIA GPU is visible but PyTorch lacks CUDA support, install the appropriate PyTorch build using the official selector: https://pytorch.org/get-started/locally/ . After CUDA is ready, install local model dependencies:

```bash
pip install -r requirements-local-video.txt
# optional: set CINEFORGE_HF_CACHE and HF_TOKEN in your environment
```

## Self-hosted video model

CineForge's local engine is implemented in `cineforge/local_video.py`. It loads Diffusers' CogVideoX pipeline inside the CineForge Python process and encodes generated frames to MP4 using PyAV. It does not send prompts to Replicate or another video-generation API and does not require ComfyUI.

1. Install a PyTorch build matching your operating system and CUDA version.
2. Install `requirements-local-video.txt`.
3. Ensure the machine has sufficient GPU memory and disk space. The first run downloads model weights.
4. Set `CINEFORGE_MODEL_ID` if using a compatible alternative model.
5. Start CineForge on the same machine as the GPU.

**Status:** Actual generation still requires testing on compatible GPU hardware. Codespaces environments commonly lack a GPU; the app reports not-ready rather than running the model on CPU.

## No FFmpeg executable

CineForge uses PyAV for media processing and does not call the FFmpeg executable. PyAV may use FFmpeg libraries internally.

## Existing studio features

Storyboard planning, scene review and editing, project library, workspace isolation, checkpoints, retry/recovery, bilingual narration, timeline tools, audio mixing, quality checks and final MP4 assembly remain part of the app.
