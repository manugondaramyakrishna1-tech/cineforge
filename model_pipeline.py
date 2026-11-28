"""Reusable GPU text-to-video inference pipeline for CineForge."""
import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

MODEL_ID = "THUDM/CogVideoX-2b"

def load_model(model_id=MODEL_ID):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU unavailable. Run this on a cloud GPU host.")
    pipeline = CogVideoXPipeline.from_pretrained(model_id, torch_dtype=torch.float16)
    pipeline.enable_model_cpu_offload()
    pipeline.vae.enable_tiling()
    pipeline.vae.enable_slicing()
    return pipeline

def generate_video(prompt, output_path="outputs/video.mp4", model_id=MODEL_ID,
                   num_frames=25, steps=25, guidance=6.0, seed=42, progress_callback=None):
    pipeline = load_model(model_id)
    generator = torch.Generator(device="cuda").manual_seed(seed)
    frames = pipeline(prompt=prompt, num_frames=num_frames,
                      num_inference_steps=steps, guidance_scale=guidance,
                      generator=generator, callback_on_step_end=(lambda pipe, step, timestep, kwargs: (progress_callback(step + 1, steps) if progress_callback else None, kwargs)[1])).frames[0]
    export_to_video(frames, output_path, fps=8)
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--output", default="outputs/video.mp4")
    parser.add_argument("--model", default=MODEL_ID)
    parser.add_argument("--frames", type=int, default=25)
    parser.add_argument("--steps", type=int, default=25)
    args = parser.parse_args()
    print(generate_video(args.prompt, args.output, args.model, args.frames, args.steps))
