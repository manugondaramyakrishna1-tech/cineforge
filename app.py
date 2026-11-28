import streamlit as st
import torch
from pathlib import Path
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

st.set_page_config(page_title="CineForge GPU Video Studio", page_icon="🎬", layout="wide")
st.title("🎬 CineForge — Cloud GPU Video Studio")
st.caption("PyTorch + Diffusers + CogVideoX")

def gpu_report():
    info = {"cuda": torch.cuda.is_available(), "torch": torch.__version__,
            "cuda_version": torch.version.cuda, "count": torch.cuda.device_count()}
    if info["cuda"]:
        info["name"] = torch.cuda.get_device_name(0)
        info["memory_total"] = torch.cuda.get_device_properties(0).total_memory
        info["memory_allocated"] = torch.cuda.memory_allocated(0)
        info["memory_reserved"] = torch.cuda.memory_reserved(0)
    return info

@st.cache_resource(show_spinner=False)
def load_pipeline(model_id):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU unavailable. This Python runtime does not currently expose a CUDA GPU.")
    pipe = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()
    return pipe

with st.sidebar:
    model_id = st.text_input("Model ID", "THUDM/CogVideoX-2b")
    steps = st.slider("Inference steps", 10, 50, 25, 5)
    frames = st.select_slider("Frames", options=[17, 25, 33, 49], value=25)
    guidance = st.slider("Guidance", 1.0, 10.0, 6.0, 0.5)
    seed = st.number_input("Seed", min_value=0, max_value=9999999, value=42)

st.subheader("Runtime diagnostics")
report = gpu_report()
c1, c2, c3 = st.columns(3)
c1.metric("CUDA", "Available" if report["cuda"] else "Unavailable")
c2.metric("PyTorch", report["torch"])
c3.metric("CUDA build", report["cuda_version"] or "CPU-only build")
if report["cuda"]:
    st.success(f"GPU detected: {report['name']}")
    st.write(f"GPU count: {report['count']}")
    st.write(f"VRAM total: {report['memory_total'] / (1024**3):.2f} GiB")
    st.write(f"VRAM allocated: {report['memory_allocated'] / (1024**3):.2f} GiB")
    st.write(f"VRAM reserved: {report['memory_reserved'] / (1024**3):.2f} GiB")
else:
    st.warning("No CUDA GPU is exposed to this runtime. The app cannot enable a GPU by itself.")
    with st.expander("Troubleshooting"):
        st.markdown("""
        1. Check whether your runtime/provider actually offers a GPU.
        2. Restart or reconnect to a GPU-enabled runtime/session.
        3. Verify PyTorch is a CUDA-enabled build, not a CPU-only build.
        4. In a terminal, run: `python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"`
        5. If CUDA availability remains False, this is a runtime/installation issue—not a prompt or video-generation setting.
        """)
        st.info("A local PC, Codespace, or container without GPU hardware or GPU passthrough will not detect a CUDA GPU.")

prompt = st.text_area("Video prompt", height=130)
negative = st.text_input("Negative prompt", "blurry, flickering, low quality")
if st.button("Generate video", type="primary", disabled=not prompt.strip() or not report["cuda"]):
    load_status = st.status("Preparing GPU model…", expanded=True)
    try:
        load_status.write("Loading model and checking CUDA resources.")
        pipe = load_pipeline(model_id.strip())
        load_status.update(label="Model loaded. Generating video…", state="running")
        with st.spinner("Generating video—this may take several minutes."):
            result = pipe(prompt=prompt.strip(), negative_prompt=negative or None,
                          num_frames=int(frames), num_inference_steps=int(steps),
                          guidance_scale=float(guidance),
                          generator=torch.Generator(device="cuda").manual_seed(int(seed)))
            out = Path("outputs")
            out.mkdir(exist_ok=True)
            path = out / "cineforge.mp4"
            export_to_video(result.frames[0], str(path), fps=8)
        load_status.update(label="Video generated successfully", state="complete")
        st.video(str(path))
        st.download_button("Download MP4", path.read_bytes(), "cineforge.mp4", "video/mp4")
    except Exception as e:
        load_status.update(label="Generation failed", state="error")
        st.error(f"Pipeline error: {e}")
