"""FastAPI video API with persistent SQLite job history."""
import uuid, threading, subprocess, sqlite3, json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import torch
from model_pipeline import generate_video, MODEL_ID

app = FastAPI(title="CineForge Video API", version="1.3.0")
executor = ThreadPoolExecutor(max_workers=1)
jobs = {}
lock = threading.Lock()
OUTPUT_DIR = Path("outputs"); OUTPUT_DIR.mkdir(exist_ok=True)
DB_PATH = Path("cineforge_jobs.sqlite3")

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS jobs (
          job_id TEXT PRIMARY KEY, prompt TEXT NOT NULL, status TEXT NOT NULL,
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, output TEXT,
          error TEXT, settings TEXT NOT NULL)""")
        c.execute("UPDATE jobs SET status='failed', error='Interrupted by server restart', updated_at=? WHERE status IN ('queued','running')", (now(),))
    reload_jobs()

def reload_jobs():
    with db() as c:
        rows=c.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    for row in rows:
        j=dict(row); j["settings"]=json.loads(j["settings"])
        jobs[j["job_id"]]=j

init_db()

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    model_id: str = MODEL_ID
    frames: int = Field(default=25, ge=17, le=49)
    steps: int = Field(default=25, ge=1, le=50)
    guidance: float = Field(default=6.0, ge=1.0, le=10.0)
    seed: int = Field(default=42, ge=0, le=9999999)

def gpu_report():
    available=torch.cuda.is_available()
    result={"status":"ok","cuda_available":available,"torch_version":str(torch.__version__),
      "cuda_build":torch.version.cuda,"gpu":None,"memory":None,"device_count":torch.cuda.device_count(),
      "runtime_hint":None,"nvidia_smi":None}
    if available:
        d=torch.cuda.get_device_properties(0); result["gpu"]=d.name
        result["memory"]={"total_bytes":d.total_memory,"allocated_bytes":torch.cuda.memory_allocated(0),"reserved_bytes":torch.cuda.memory_reserved(0)}
    else:
        result["runtime_hint"]="CUDA-enabled PyTorch is installed, but no GPU is visible. Attach a compatible GPU to this host."
        try:
            p=subprocess.run(["nvidia-smi"],capture_output=True,text=True,timeout=3)
            result["nvidia_smi"]={"available":p.returncode==0,"output":p.stdout[:2000] if p.returncode==0 else p.stderr[:500]}
        except (FileNotFoundError,subprocess.TimeoutExpired):
            result["nvidia_smi"]={"available":False,"output":"nvidia-smi is not installed or unavailable"}
    return result

def persist(j):
    with db() as c:
        c.execute("""INSERT OR REPLACE INTO jobs(job_id,prompt,status,created_at,updated_at,output,error,settings)
        VALUES(?,?,?,?,?,?,?,?)""",(j["job_id"],j["prompt"],j["status"],j["created_at"],j["updated_at"],j.get("output"),j.get("error"),json.dumps(j["settings"])))

def update_job(job_id, **changes):
    with lock:
        jobs[job_id].update(changes,updated_at=now())
        snapshot=dict(jobs[job_id])
    persist(snapshot)

def worker(job_id, request):
    update_job(job_id,status="running")
    try:
        path=OUTPUT_DIR/f"{job_id}.mp4"
        generate_video(request.prompt,str(path),request.model_id,request.frames,request.steps,request.guidance,request.seed)
        update_job(job_id,status="completed",output=str(path),error=None)
    except Exception as exc:
        update_job(job_id,status="failed",error=str(exc))

@app.get("/health")
def health(): return gpu_report()

@app.post("/jobs",status_code=202)
def create_job(request:GenerateRequest):
    report=gpu_report()
    if not report["cuda_available"]: raise HTTPException(status_code=503,detail=report["runtime_hint"])
    job_id=str(uuid.uuid4()); stamp=now()
    settings=request.model_dump() if hasattr(request,"model_dump") else request.dict()
    j={"job_id":job_id,"prompt":request.prompt,"status":"queued","created_at":stamp,"updated_at":stamp,"output":None,"error":None,"settings":settings}
    with lock: jobs[job_id]=j
    persist(j)
    executor.submit(worker,job_id,request)
    return {"job_id":job_id,"status":"queued","status_url":f"/jobs/{job_id}"}

@app.get("/jobs")
def list_jobs(limit:int=50):
    limit=max(1,min(limit,200))
    with db() as c: rows=c.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
    out=[]
    for row in rows:
        j=dict(row); j["settings"]=json.loads(j["settings"])
        if j["status"]=="completed": j["download_url"]=f"/jobs/{j['job_id']}/video"
        j.pop("output",None); out.append(j)
    return {"jobs":out}

@app.get("/jobs/{job_id}")
def get_job(job_id:str):
    with lock:
        job=jobs.get(job_id)
        if not job: raise HTTPException(404,detail="Job not found")
        result=dict(job)
    if result["status"]=="completed": result["download_url"]=f"/jobs/{job_id}/video"; result.pop("output",None)
    return result

@app.get("/jobs/{job_id}/video")
def download_video(job_id:str):
    with lock:
        job=jobs.get(job_id)
        if not job: raise HTTPException(404,detail="Job not found")
        if job["status"]!="completed": raise HTTPException(409,detail=f"Job is {job['status']}")
        path=job["output"]
    if not Path(path).exists(): raise HTTPException(410,detail="Video file is missing")
    return FileResponse(path,media_type="video/mp4",filename=f"cineforge-{job_id}.mp4")

@app.get("/",include_in_schema=False)
def mobile_frontend(): return FileResponse("mobile.html",media_type="text/html")
