# CineForge AI — cinematic video creation

CineForge is a Python Streamlit studio for prompt-to-storyboard planning, scene editing, hosted or self-hosted AI scene rendering, narration, timeline assembly and MP4 export. It does **not** invoke the FFmpeg executable.

## Requirements
- Python 3.10+
- Hosted mode: a Replicate API token stored on the CineForge server and a model-specific JSON input template
- Self-hosted mode: ComfyUI reachable from CineForge, a compatible video model/workflow and the required compute hardware

## Run
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Hosted video generation (no ComfyUI server)

1. Select **Hosted (Replicate)** in the CineForge sidebar.
2. Configure `REPLICATE_API_TOKEN` on the machine running CineForge, or in Streamlit secrets. Do not paste the token into source files, upload it as a project file, or commit it to GitHub.
3. Upload a JSON template matching the selected model's API input schema. Example shape:

```json
{
  "model": "owner/model",
  "input": {
    "prompt": "__PROMPT__",
    "negative_prompt": "__NEGATIVE__",
    "duration": "__DURATION__",
    "aspect_ratio": "__ASPECT_RATIO__"
  }
}
```

The example field names are illustrative only. Each hosted model has its own required input schema; use the model's API documentation to choose valid fields and values. CineForge replaces the prompt tokens per scene. A token placed alone as a JSON value (such as `"__DURATION__"`) is replaced with its native value type.

Hosted generation is provided by a third party and may incur usage charges. Review model pricing and limits with a parent or guardian before enabling paid usage. Model output formats and availability vary; CineForge validates and downloads supported video outputs.

## Self-hosted ComfyUI mode

1. Select **ComfyUI (self-hosted)**.
2. Prepare a text-to-video workflow with a video output node.
3. Export the workflow in ComfyUI API format.
4. Replace the positive prompt with `__PROMPT__` and optionally use `__NEGATIVE__`.
5. Enter the private ComfyUI URL and upload the API workflow JSON.

Do not expose an unauthenticated ComfyUI port to the public internet. If CineForge and ComfyUI share one machine, bind ComfyUI to loopback and use `http://127.0.0.1:8188`.

## Existing studio features

Storyboard planning, scene review and editing, project library, workspace isolation, checkpoints, retry/recovery, bilingual narration, timeline tools, audio mixing, quality checks and final MP4 assembly remain part of the app.

PyAV may use FFmpeg libraries internally, but CineForge does not call the FFmpeg executable. Hosted video generation depends on the selected model's provider API and output schema.
