"""Generate a local AI still and render it as a moving MP4 scene using PyAV."""
from pathlib import Path
import argparse
import numpy as np
import av
from PIL import Image

from generate_ai_scene import main as _unused  # keep generator dependency visible
from diffusers import AutoPipelineForText2Image
import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default="outputs/ai_scene_video.mp4")
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--fps", type=int, default=24)
    args = parser.parse_args()

    image = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sd-turbo", torch_dtype=torch.float32, use_safetensors=True
    ).to("cpu")
    image.enable_attention_slicing()
    still = image(prompt=args.prompt, num_inference_steps=1, guidance_scale=0.0,
                  height=512, width=512).images[0]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    width, height = 640, 360
    frames = int(args.seconds * args.fps)
    base = still.convert("RGB")
    # Crop to wide aspect then apply gradual zoom for cinematic motion.
    crop_width = 512
    crop_height = int(crop_width * height / width)
    container = av.open(str(output), "w")
    stream = container.add_stream("libx264", rate=args.fps)
    stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
    stream.options = {"preset": "medium", "crf": "23"}
    try:
        for i in range(frames):
            zoom = 1.0 + 0.06 * i / max(1, frames - 1)
            cw, ch = int(crop_width / zoom), int(crop_height / zoom)
            left = (512 - cw) // 2
            top = (512 - ch) // 2
            frame_image = base.crop((left, top, left + cw, top + ch)).resize((width, height))
            rgb = np.asarray(frame_image, dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(rgb, format="rgb24")
            frame.pts = i
            frame.time_base = stream.time_base
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    finally:
        container.close()
    print(f"Saved scene MP4: {output.resolve()}")

if __name__ == "__main__":
    main()
