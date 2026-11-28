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

## Self-hosted video model

CineForge's local engine is implemented in `cineforge/local_video.py`. It loads Diffusers' CogVideoX pipeline inside the CineForge Python process and encodes generated frames to MP4 using PyAV. It does not send prompts to Replicate or another video-generation API and does not require ComfyUI.

1. Install the PyTorch build that matches your operating system and CUDA version from the official PyTorch installation selector: https://pytorch.org/get-started/locally/
2. Install the optional model dependencies:
   ```bash
   pip install -r requirements-local-video.txt
   ```
3. Ensure the machine has enough GPU memory and disk space for the selected model. The first run downloads model weights and may take a long time.
4. Set `CINEFORGE_MODEL_ID` to a compatible Diffusers CogVideoX model ID if you are not using the default.
5. Start CineForge on the same machine as the GPU.

**Important:** The local inference module is implemented, but the Streamlit render controls are not yet switched over to it. The current app UI still contains the earlier provider selector. Do not configure a Replicate token or expose a ComfyUI server as a workaround; UI integration is the next implementation step. Actual generation has not yet been verified on a GPU in this repository.

## No FFmpeg executable

CineForge uses PyAV for media processing and does not call the FFmpeg executable. PyAV may use FFmpeg libraries internally.

## Existing studio features

Storyboard planning, scene review and editing, project library, workspace isolation, checkpoints, retry/recovery, bilingual narration, timeline tools, audio mixing, quality checks and final MP4 assembly remain part of the app.
