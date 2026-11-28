"""GPU runtime diagnostics for CineForge (CUDA-only)."""
import platform
import torch

def gpu_report():
    return {
        "python_platform": platform.platform(),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "device_count": torch.cuda.device_count(),
        "memory_total_gb": round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2) if torch.cuda.is_available() else None,
    }

def require_cuda():
    if not torch.cuda.is_available():
        raise RuntimeError("No CUDA GPU is visible. Start a GPU-enabled cloud runtime, install compatible CUDA PyTorch, then restart.")
    return torch.device("cuda")
