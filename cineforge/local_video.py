"""Self-hosted CogVideoX text-to-video adapter.

This module runs model inference in the CineForge Python process. It does not call
ComfyUI, Replicate, or another generation API. Model weights are downloaded from
the configured Hugging Face model repository on first use and cached locally.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from fractions import Fraction
from typing import Any


DEFAULT_MODEL = "THUDM/CogVideoX-2b"


def runtime_status() -> dict[str, Any]:
    """Describe local inference readiness without downloading model weights."""
    try:
        import torch
    except ImportError:
        return {
            "ready": False,
            "device": "unavailable",
            "message": "PyTorch is not installed. Install the optional local-video requirements.",
        }
    if torch.cuda.is_available():
        device = "cuda"
        detail = torch.cuda.get_device_name(0)
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        device = "mps"
        detail = "Apple Metal"
    else:
        device = "cpu"
        detail = "CPU detected; CogVideoX generation is not enabled on CPU because it is impractically slow and memory intensive."
    return {
        "ready": device in {"cuda", "mps"},
        "device": device,
        "detail": detail,
        "message": (
            f"Local inference device: {detail}."
            if device in {"cuda", "mps"}
            else detail
        ),
    }




def gpu_memory_status() -> dict[str, Any]:
    """Return CUDA memory telemetry when CUDA is visible; never invent GPU access."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"available": False, "device": runtime_status().get("device", "unknown")}
        free, total = torch.cuda.mem_get_info(0)
        return {"available": True, "device": torch.cuda.get_device_name(0),
                "free_bytes": int(free), "total_bytes": int(total),
                "allocated_bytes": int(torch.cuda.memory_allocated(0)),
                "reserved_bytes": int(torch.cuda.memory_reserved(0))}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


def cleanup_gpu_memory() -> dict[str, Any]:
    """Safely release cached CUDA allocations if CUDA is actually available."""
    try:
        import gc
        import torch
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
            return gpu_memory_status()
        return {"available": False, "message": "CUDA not available; Python garbage collection ran."}
    except Exception as exc:
        return {"available": False, "error": str(exc)}


class LocalCogVideoX:
    """In-process CogVideoX inference with a small render interface.

    The first call loads model weights and can take several minutes. A compatible
    GPU and substantial available memory are required. No hosted inference API is
    contacted; Hugging Face is used only as the model-weight distribution source.
    """

    def __init__(self, model_id: str | None = None, output_fps: int = 8):
        self.model_id = (model_id or os.environ.get("CINEFORGE_MODEL_ID") or DEFAULT_MODEL).strip()
        self.output_fps = max(1, min(30, int(output_fps)))
        self._pipeline = None
        self._pending: dict[str, Any] | None = None
        self._frames = None

    def _load_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        status = runtime_status()
        if not status["ready"]:
            raise RuntimeError(status["message"])
        try:
            import torch
            from diffusers import CogVideoXPipeline
        except ImportError as exc:
            raise RuntimeError(
                "Local video dependencies are missing. Install requirements-local-video.txt "
                "inside the CineForge environment."
            ) from exc

        dtype = torch.float16 if status["device"] == "cuda" else torch.float32
        try:
            pipe = CogVideoXPipeline.from_pretrained(self.model_id, torch_dtype=dtype)
            if status["device"] == "cuda":
                pipe.enable_model_cpu_offload()
            else:
                pipe.to("mps")
        except Exception as exc:
            raise RuntimeError(
                f"Could not load local model '{self.model_id}'. Check model access, disk space, "
                f"GPU memory and the installed Diffusers version: {exc}"
            ) from exc
        self._pipeline = pipe
        return pipe

    def submit(self, request: dict[str, Any]) -> str:
        if not isinstance(request, dict) or not str(request.get("prompt", "")).strip():
            raise ValueError("A non-empty scene prompt is required.")
        self._pending = {
            "prompt": str(request["prompt"]).strip(),
            "negative_prompt": str(request.get("negative_prompt", "")).strip(),
            "num_frames": max(9, min(49, int(request.get("num_frames", 49)))),
            "steps": max(1, min(50, int(request.get("steps", 30)))),
            "guidance_scale": float(request.get("guidance_scale", 6.0)),
            "seed": request.get("seed"),
            "width": max(64, min(1280, int(request.get("width", 720)))),
            "height": max(64, min(1280, int(request.get("height", 480)))),
        }
        # H.264 yuv420p requires even dimensions.
        self._pending["width"] -= self._pending["width"] % 2
        self._pending["height"] -= self._pending["height"] % 2
        self._frames = None
        self._output_size = (self._pending["width"], self._pending["height"])
        return str(int(time.time() * 1000))

    def wait_for_outputs(self, job_id: str, status_box=None, timeout: int = 3600):
        if self._pending is None:
            raise RuntimeError("No local generation request has been submitted.")
        if status_box is not None:
            status_box.info("Loading the local video model and generating frames. First run downloads model weights.")
        started = time.monotonic()
        pipe = self._load_pipeline()
        import torch

        generator = None
        seed = self._pending.get("seed")
        if seed is not None:
            generator_device = "cuda" if torch.cuda.is_available() else "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu"
            generator = torch.Generator(device=generator_device).manual_seed(int(seed))
        try:
            result = pipe(
                prompt=self._pending["prompt"],
                negative_prompt=self._pending["negative_prompt"] or None,
                num_frames=self._pending["num_frames"],
                num_inference_steps=self._pending["steps"],
                guidance_scale=self._pending["guidance_scale"],
                width=self._pending["width"],
                height=self._pending["height"],
                generator=generator,
            )
        except Exception as exc:
            raise RuntimeError(f"Local CogVideoX inference failed: {exc}") from exc
        if time.monotonic() - started > max(1, int(timeout)):
            raise TimeoutError("Local video generation exceeded the configured timeout.")
        frames = getattr(result, "frames", None)
        if not frames or not frames[0]:
            raise RuntimeError("Local video model returned no frames.")
        self._frames = frames[0]
        self._pending = None
        if status_box is not None:
            status_box.success(f"Local model generated {len(self._frames)} frames.")
            if memory_after.get("available"):
                status_box.caption(f"GPU memory allocated: {memory_after.get('allocated_bytes', 0) / 1024**3:.2f} GiB; reserved: {memory_after.get('reserved_bytes', 0) / 1024**3:.2f} GiB.")
        return {"frames": len(self._frames)}

    def download_videos(self, prediction, folder: str | Path) -> list[Path]:
        """Encode generated PIL frames to MP4 with PyAV (no ffmpeg executable)."""
        if self._frames is None:
            raise RuntimeError("No generated frames are available to encode.")
        try:
            import av
            import numpy as np
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise RuntimeError("PyAV and NumPy are required to encode the local video.") from exc

        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / "local_scene.mp4"
        temporary = target.with_suffix(".mp4.part")
        first = self._frames[0]
        width, height = first.size
        container = av.open(str(temporary), mode="w", format="mp4")
        try:
            stream = container.add_stream("libx264", rate=self.output_fps)
            stream.width = width
            stream.height = height
            stream.pix_fmt = "yuv420p"
            stream.time_base = Fraction(1, self.output_fps)
            stream.options = {"preset": "medium", "crf": "23"}
            for frame_index, image in enumerate(self._frames):
                image = ImageOps.fit(image.convert("RGB"), (width, height), method=Image.Resampling.LANCZOS)
                array = np.asarray(image)
                frame = av.VideoFrame.from_ndarray(array, format="rgb24")
                frame.pts = frame_index
                frame.time_base = Fraction(1, self.output_fps)
                for packet in stream.encode(frame):
                    container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        finally:
            container.close()
        temporary.replace(target)
        self._frames = None
        return [target]
