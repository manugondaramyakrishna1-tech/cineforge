# CineForge AI — MVP completion checklist

## Implemented modules
- Streamlit studio, storyboard planning and scene review
- ComfyUI workflow submission and video-output collection
- Project JSON save/import helpers and library
- Scene ordering, preview and CSV timeline export
- Scene render-status registry, checkpointing and replacement manifest
- Narration generation and sound-mix helpers
- PyAV-based clip assembly and audio muxing (no FFmpeg executable invocation)
- Export preset definitions and reliability helpers

## Run locally
1. Install Python 3.10 or newer.
2. Install dependencies: `pip install -r requirements.txt`
3. Start ComfyUI and prepare a compatible API workflow.
4. Run: `streamlit run app.py`
5. Upload the API workflow JSON, review the scenes and configure output.

## Validation before production
- [ ] Run tests: `python -m unittest discover -s tests`
- [ ] Confirm ComfyUI and workflow/model dependencies are available.
- [ ] Test with a short sample clip before a full project.
- [ ] Inspect final audio/video synchronization and export dimensions.
- [ ] Back up the projects and outputs folders.

## Known limitations
- Export preset dimensions are displayed as workflow guidance; the current assembly function does not yet apply preset-specific scaling. Configure dimensions in the uploaded ComfyUI workflow.
- Sound fade settings shown in the UI are not fully connected to all audio-mixing paths.
- Full end-to-end rendering and test suite have not been verified in this repository environment.
- ComfyUI/model performance and availability depend on the user's hardware and installed workflow.

## Safety and deployment
Do not expose ComfyUI to an untrusted network. Keep model/workflow dependencies and any credentials under local control. CineForge does not invoke the FFmpeg command-line executable; PyAV may rely on FFmpeg libraries internally.
