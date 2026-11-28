"""FastAPI job API for CineForge. GPU execution occurs on the host running this service."""
import uuid, threading, subprocess, os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import torch
from model_pipeline import generate_video, MODEL_ID

app = FastAPI(title="CineForge Video API", version="1.2.0")
executor = ThreadPoolExecutor(max_workers=1)
jobs = {}
lock = threading.Lock()
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    model_id: str = MODEL_ID
    frames: int = Field(default=25, ge=17, le=49)
    steps: int = Field(default=25, ge=1, le=50)
    guidance: float = Field(default=6.0, ge=1.0, le=10.0)
    seed: int = Field(default=42, ge=0, le=9999999)

def gpu_report():
    available = torch.cuda.is_available()
    result = {"status":"ok", "cuda_available":available, "torch_version":str(torch.__version__),
              "cuda_build":torch.version.cuda, "gpu":None, "memory":None,
              "device_count":torch.cuda.device_count(), "runtime_hint":None,
              "nvidia_smi":None}
    if available:
        device = torch.cuda.get_device_properties(0)
        result["gpu"] = device.name
        result["memory"] = {"total_bytes":device.total_memory,
            "allocated_bytes":torch.cuda.memory_allocated(0),
            "reserved_bytes":torch.cuda.memory_reserved(0)}
    else:
        result["runtime_hint"] = ("CUDA-enabled PyTorch is installed, but no GPU is visible. "
          "Attach an NVIDIA GPU to this host/container and ensure drivers and GPU passthrough are configured.")
        try:
            p=subprocess.run(["nvidia-smi"],capture_output=True,text=True,timeout=3)
            result["nvidia_smi"]={"available":p.returncode==0,"output":p.stdout[:2000] if p.returncode==0 else p.stderr[:500]}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            result["nvidia_smi"]={"available":False,"output":"nvidia-smi is not installed or unavailable in this runtime"}
    return result

def worker(job_id, request):
    with lock: jobs[job_id]["status"]="running"
    try:
        path=OUTPUT_DIR/f"{job_id}.mp4"
        generate_video(request.prompt,str(path),request.model_id,request.frames,request.steps,request.guidance,request.seed)
        with lock: jobs[job_id].update(status="completed",output=str(path))
    except Exception as exc:
        with lock: jobs[job_id].update(status="failed",error=str(exc))

@app.get("/health")
def health():
    return gpu_report()

@app.post("/jobs",status_code=202)
def create_job(request:GenerateRequest):
    report=gpu_report()
    if not report["cuda_available"]:
        raise HTTPException(status_code=503,detail=report["runtime_hint"])
    job_id=str(uuid.uuid4())
    with lock: jobs[job_id]={"job_id":job_id,"status":"queued"}
    executor.submit(worker,job_id,request)
    return {"job_id":job_id,"status":"queued","status_url":f"/jobs/{job_id}"}

@app.get("/jobs/{job_id}")
def get_job(job_id:str):
    with lock:
        job=jobs.get(job_id)
        if not job: raise HTTPException(status_code=404,detail="Job not found")
        result=dict(job)
    if result.get("status")=="completed":
        result["download_url"]=f"/jobs/{job_id}/video"
        result.pop("output",None)
    return result

@app.get("/jobs/{job_id}/video")
def download_video(job_id:str):
    with lock:
        job=jobs.get(job_id)
        if not job: raise HTTPException(status_code=404,detail="Job not found")
        if job["status"]!="completed": raise HTTPException(status_code=409,detail=f"Job is {job['status']}")
        path=job["output"]
    return FileResponse(path,media_type="video/mp4",filename=f"cineforge-{job_id}.mp4")

@app.get("/",include_in_schema=False)
def mobile_frontend():
    return FileResponse("mobile.html",media_type="text/html")
