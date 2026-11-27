# CineForge AI — real text-to-video workflow

This Python Streamlit app submits a ComfyUI API workflow to a running ComfyUI server, waits for its completion, and downloads video outputs. It does **not** call FFmpeg.

## Requirements
- Python 3.10+
- ComfyUI running and reachable (typically http://127.0.0.1:8188 when local)
- A compatible text-to-video model and workflow installed in ComfyUI
- Workflow exported in ComfyUI API format JSON

## Run
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Workflow preparation
1. In ComfyUI, prepare a text-to-video workflow with a video output node.
2. Export/save the workflow in API format.
3. Replace the positive text prompt with `__PROMPT__` and negative text prompt with `__NEGATIVE__` in the workflow JSON.
4. Upload that JSON in CineForge and generate.

The workflow/model is responsible for actual video synthesis. CineForge is the Python orchestration UI; it does not contain model weights. Model availability, hardware requirements and output nodes vary by workflow.

## Notes
- Do not expose ComfyUI to the public internet without appropriate security controls.
- This application makes no FFmpeg executable calls. ComfyUI/model workflows may have their own dependencies.
