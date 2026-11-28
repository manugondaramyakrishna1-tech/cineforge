"""Generate a local AI scene image with Stable Diffusion Turbo.

The model weights are downloaded from Hugging Face on first run.
Inference itself runs locally on CPU; expect slow generation and high RAM use.
This creates a still image, not a video diffusion clip.
"""
from pathlib import Path
import argparse

import torch
from diffusers import AutoPipelineForText2Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", default="outputs/ai_scene.png")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    pipeline = AutoPipelineForText2Image.from_pretrained(
        "stabilityai/sd-turbo",
        torch_dtype=torch.float32,
        use_safetensors=True,
    )
    pipeline.to("cpu")
    pipeline.enable_attention_slicing()

    image = pipeline(
        prompt=args.prompt,
        num_inference_steps=1,
        guidance_scale=0.0,
        height=512,
        width=512,
    ).images[0]
    image.save(output)
    print(f"Saved AI scene: {output.resolve()}")


if __name__ == "__main__":
    main()
