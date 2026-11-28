"""CUDA runtime diagnostics for CineForge."""
import platform, subprocess, torch

def gpu_report():
    available=torch.cuda.is_available()
    result={"python_platform":platform.platform(),"torch_version":str(torch.__version__),
        "cuda_available":available,"cuda_version":torch.version.cuda,
        "device_name":torch.cuda.get_device_name(0) if available else None,
        "device_count":torch.cuda.device_count(),
        "memory_total_gb":round(torch.cuda.get_device_properties(0).total_memory/1024**3,2) if available else None,
        "runtime_hint":None if available else "No CUDA GPU is visible. GPU hardware and driver/passthrough must be provided by the host."}
    if not available:
        try:
            p=subprocess.run(["nvidia-smi"],capture_output=True,text=True,timeout=3)
            result["nvidia_smi_available"]=p.returncode==0
            result["nvidia_smi_output"]=p.stdout[:1500] if p.returncode==0 else p.stderr[:300]
        except (FileNotFoundError,subprocess.TimeoutExpired):
            result["nvidia_smi_available"]=False
            result["nvidia_smi_output"]="nvidia-smi unavailable"
    return result

def require_cuda():
    if not torch.cuda.is_available():
        raise RuntimeError("No CUDA GPU is visible. Attach a GPU-enabled runtime and verify host driver/passthrough.")
    return torch.device("cuda")
