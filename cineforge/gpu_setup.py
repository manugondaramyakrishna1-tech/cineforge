"""CineForge GPU setup helper.

Run: python -m cineforge.gpu_setup
This checks driver/hardware and prepares local-video Python dependencies.
It cannot provision physical GPU hardware or install NVIDIA drivers.
"""
from __future__ import annotations
import importlib.util
import platform
import subprocess
import sys

def check():
    report = {"python": sys.version.split()[0], "platform": platform.platform()}
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=10)
        report["nvidia_smi"] = result.stdout.splitlines()[0] if result.returncode == 0 and result.stdout else result.stderr.strip() or "NVIDIA tool returned no output"
        report["gpu_detected_by_driver"] = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        report["nvidia_smi"] = "Unavailable: NVIDIA driver/tool not detected"
        report["gpu_detected_by_driver"] = False
    if importlib.util.find_spec("torch"):
        import torch
        report["torch_version"] = torch.__version__
        report["cuda_available"] = torch.cuda.is_available()
        report["torch_cuda_version"] = torch.version.cuda
        report["device"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No CUDA device detected by PyTorch"
    else:
        report["torch_version"] = "not installed"
        report["cuda_available"] = False
    return report

def main():
    print("CineForge GPU diagnostics")
    report = check()
    for key, value in report.items():
        print(f"{key}: {value}")
    if not report.get("gpu_detected_by_driver"):
        print("\nGPU hardware/driver is not available to this environment.")
        print("Installing CUDA packages alone will not create GPU access.")
        print("Use a machine/runtime with an NVIDIA GPU and drivers, then rerun.")
        return 2
    if not report.get("cuda_available"):
        print("\nNVIDIA driver is detected, but PyTorch CUDA is not ready.")
        print("Install a matching PyTorch CUDA wheel from the official PyTorch selector:")
        print("https://pytorch.org/get-started/locally/")
        print("Then run: python -m cineforge.gpu_setup")
        return 1
    print("\nGPU runtime is ready for CineForge's local inference setup.")
    print("Install project video dependencies with: pip install -r requirements-local-video.txt")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
