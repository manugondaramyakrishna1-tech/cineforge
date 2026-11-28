"""CineForge GPU diagnostics.

Run: python -m cineforge.gpu_setup
This reports driver, accelerator and PyTorch visibility. It cannot provision GPU hardware.
"""
from __future__ import annotations
import importlib.util
import platform
import subprocess
import sys

def _run(command, timeout=10):
    try:
        p = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return {"returncode": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}

def check():
    report = {"python": sys.version.split()[0], "python_executable": sys.executable,
              "platform": platform.platform(), "cuda_env": {
                  key: value for key, value in __import__("os").environ.items()
                  if key.startswith(("CUDA", "NVIDIA"))}}
    smi = _run(["nvidia-smi"])
    report["nvidia_smi"] = smi["stdout"] or smi["stderr"] or "No output"
    report["driver_visible"] = smi["returncode"] == 0
    query = _run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"])
    report["gpu_details"] = query["stdout"] if query["returncode"] == 0 else query["stderr"]
    if importlib.util.find_spec("torch"):
        try:
            import torch
            report["torch_version"] = torch.__version__
            report["torch_cuda_build"] = torch.version.cuda
            report["cuda_available"] = torch.cuda.is_available()
            report["gpu_count"] = torch.cuda.device_count()
            report["device"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No CUDA device detected by PyTorch"
            if torch.cuda.is_available():
                report["cuda_runtime_test"] = "passed"
                try:
                    torch.ones(1, device="cuda")
                except Exception as exc:
                    report["cuda_runtime_test"] = f"failed: {exc}"
                    report["cuda_available"] = False
        except Exception as exc:
            report["torch_error"] = str(exc)
            report["cuda_available"] = False
    else:
        report["torch_version"] = "not installed"
        report["cuda_available"] = False
    return report

def main():
    report = check()
    print("CineForge GPU diagnostics")
    for key, value in report.items():
        print(f"{key}: {value}")
    if not report.get("driver_visible"):
        print("\nNo NVIDIA driver/GPU is visible to this environment. Installing CUDA packages alone cannot create GPU access.")
        print("Use a GPU-enabled host/runtime and rerun this diagnostic.")
        return 2
    if not report.get("cuda_available"):
        print("\nThe driver is visible but PyTorch cannot use CUDA.")
        print("Confirm PyTorch's CUDA build matches the host/runtime. Use the official selector: https://pytorch.org/get-started/locally/")
        return 1
    print("\nCUDA runtime test passed. Install local-video dependencies: pip install -r requirements-local-video.txt")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
