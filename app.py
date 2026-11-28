import streamlit as st
import torch
from pathlib import Path
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

st.set_page_config(page_title="CineForge GPU Video Studio", page_icon="🎬", layout="wide")
st.title("🎬 CineForge — Cloud GPU Video Studio")
st.caption("PyTorch + Diffusers + CogVideoX")

@st.cache_resource(show_spinner="Loading model…")
def load_pipeline(model_id):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU unavailable. Select a GPU runtime.")
    pipe = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()
    return pipe

with st.sidebar:
    model_id = st.text_input("Model ID", "THUDM/CogVideoX-2b")
    steps = st.slider("Inference steps", 10, 50, 25, 5)
    frames = st.select_slider("Frames", options=[17,25,33,49], value=25)
    guidance = st.slider("Guidance", 1.0, 10.0, 6.0, 0.5)
    seed = st.number_input("Seed", min_value=0, max_value=9999999, value=42)

if torch.cuda.is_available():
    st.success(f"GPU ready: {torch.cuda.get_device_name(0)}")
else:
    st.warning("CUDA GPU not detected.")

prompt = st.text_area("Video prompt", height=130)
negative = st.text_input("Negative prompt", "blurry, flickering, low quality")
if st.button("Generate video", type="primary", disabled=not prompt.strip()):
    try:
        pipe = load_pipeline(model_id.strip())
        with st.spinner("Generating on GPU…"):
            result = pipe(prompt=prompt.strip(), negative_prompt=negative or None, num_frames=int(frames), num_inference_steps=int(steps), guidance_scale=float(guidance), generator=torch.Generator(device="cuda").manual_seed(int(seed)))
            out = Path("outputs"); out.mkdir(exist_ok=True)
            path = out / "cineforge.mp4"
            export_to_video(result.frames[0], str(path), fps=8)
        st.video(str(path))
        st.download_button("Download MP4", path.read_bytes(), "cineforge.mp4", "video/mp4")
    except Exception as e:
        st.error(f"Pipeline error: {e}")
