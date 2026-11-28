"""CineForge: notebook-friendly one-shot video generation. Run in Kaggle/Colab GPU notebook."""
import os
from pathlib import Path
import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

MODEL_ID = os.getenv("CINEFORGE_MODEL", "THUDM/CogVideoX-2b")
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

def initialize():
    if not torch.cuda.is_available():
        raise RuntimeError("GPU is not available. Select a GPU runtime and retry.")
    print("GPU:", torch.cuda.get_device_name(0))
    pipe = CogVideoXPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()
    return pipe

def generate(pipe, prompt, filename="cineforge.mp4", frames=25, steps=25, seed=42):
    if not prompt or len(prompt.strip()) < 3:
        raise ValueError("Please provide a descriptive prompt.")
    generator = torch.Generator(device="cuda").manual_seed(seed)
    result = pipe(prompt=prompt, num_frames=frames, num_inference_steps=steps, generator=generator).frames[0]
    path = OUTPUT_DIR / filename
    export_to_video(result, str(path), fps=8)
    print("Saved:", path.resolve())
    return path

if __name__ == "__main__":
    pipe = initialize()
    generate(pipe, input("Describe your video: "))
