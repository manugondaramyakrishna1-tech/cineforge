"""FastAPI video API with persistent SQLite job history."""
import uuid, threading, subprocess, sqlite3, json, time, os, secrets
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import torch
from model_pipeline import generate_video, MODEL_ID, backend_status

app = FastAPI(title="CineForge Video API", version="1.3.0")
executor = ThreadPoolExecutor(max_workers=1)
submitted = {}
jobs = {}
lock = threading.Lock()
OUTPUT_DIR = Path("outputs"); OUTPUT_DIR.mkdir(exist_ok=True)
DB_PATH = Path("cineforge_jobs.sqlite3")
last_worker_seen = None

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
          created_at TEXT NOT NULL, updated_at TEXT NOT NULL, output TEXT, progress INTEGER DEFAULT 0, stage TEXT, started_at TEXT, elapsed_seconds REAL,
          error TEXT, settings TEXT NOT NULL)""")
        c.execute("UPDATE jobs SET status='failed', error='Interrupted by server restart', updated_at=? WHERE status IN ('queued','running')", (now(),))

def ensure_columns():
    with db() as c:
        cols={r["name"] for r in c.execute("PRAGMA table_info(jobs)").fetchall()}
        for name, typ in [("progress","INTEGER DEFAULT 0"),("stage","TEXT"),("started_at","TEXT"),("elapsed_seconds","REAL")]:
            if name not in cols: c.execute("ALTER TABLE jobs ADD COLUMN "+name+" "+typ)
def reload_jobs():
    with db() as c:
        rows=c.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    for row in rows:
        j=dict(row); j["settings"]=json.loads(j["settings"])
        jobs[j["job_id"]]=j

init_db()
ensure_columns()
reload_jobs()

class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    model_id: str = MODEL_ID
    frames: int = Field(default=25, ge=17, le=49)
    steps: int = Field(default=25, ge=1, le=50)
    guidance: float = Field(default=6.0, ge=1.0, le=10.0)
    seed: int = Field(default=42, ge=0, le=9999999)

def gpu_metrics():
    try:
        p=subprocess.run(["nvidia-smi","--query-gpu=utilization.gpu,memory.used,memory.total","--format=csv,noheader,nounits"],capture_output=True,text=True,timeout=3)
        if p.returncode!=0: return {"available":False,"error":p.stderr[:300]}
        vals=p.stdout.strip().split(",")
        if len(vals)<3: return {"available":False,"error":"Unexpected nvidia-smi output"}
        return {"available":True,"utilization_percent":int(vals[0].strip()),"memory_used_mb":int(vals[1].strip()),"memory_total_mb":int(vals[2].strip())}
    except (FileNotFoundError,subprocess.TimeoutExpired) as e: return {"available":False,"error":str(e)}

@app.get("/monitor")
def monitor():
    active=next((dict(j) for j in jobs.values() if j["status"]=="running"),None)
    if active: active.pop("output",None)
    return {"gpu":gpu_metrics(),"queue":queue_snapshot(),"active_job":active}

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
        c.execute("""INSERT OR REPLACE INTO jobs(job_id,prompt,status,created_at,updated_at,output,error,settings,progress,stage,started_at,elapsed_seconds)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",(j["job_id"],j["prompt"],j["status"],j["created_at"],j["updated_at"],j.get("output"),j.get("error"),json.dumps(j["settings"]),j.get("progress",0),j.get("stage"),j.get("started_at"),j.get("elapsed_seconds")))

def update_job(job_id, **changes):
    with lock:
        jobs[job_id].update(changes,updated_at=now())
        snapshot=dict(jobs[job_id])
    persist(snapshot)

def worker(job_id, request):
    started=time.monotonic()
    update_job(job_id,status="running",stage="Loading model",progress=0,started_at=now(),elapsed_seconds=0)
    def on_step(step,total):
        update_job(job_id,stage="Generating frames",progress=int(step*100/max(total,1)),elapsed_seconds=round(time.monotonic()-started,1))
    try:
        path=OUTPUT_DIR/f"{job_id}.mp4"
        generate_video(request.prompt,str(path),request.model_id,request.frames,request.steps,request.guidance,request.seed,progress_callback=on_step)
        update_job(job_id,status="completed",stage="Complete",progress=100,output=str(path),error=None,elapsed_seconds=round(time.monotonic()-started,1))
    except Exception as exc:
        update_job(job_id,status="failed",stage="Failed",error=str(exc),elapsed_seconds=round(time.monotonic()-started,1))

def queue_snapshot():
    queued=sorted((j for j in jobs.values() if j["status"]=="queued"),key=lambda j:j["created_at"])
    running=next((j for j in jobs.values() if j["status"]=="running"),None)
    return {"busy":running is not None,"running_job_id":running["job_id"] if running else None,"queued_count":len(queued),"queue":[{"job_id":j["job_id"],"position":i+1} for i,j in enumerate(queued)]}

@app.get("/queue")
def get_queue(): return queue_snapshot()

@app.get("/health")
def health():
    report=gpu_report(); report["backend"]=backend_status(); return report

@app.post("/jobs",status_code=202)
def create_job(request:GenerateRequest):
    report=gpu_report()
    bridge_enabled=bool(os.getenv("CINEFORGE_FREE_GPU_BRIDGE_TOKEN"))
    if not report["cuda_available"] and not backend_status()["endpoint_configured"] and not bridge_enabled: raise HTTPException(status_code=503,detail=report["runtime_hint"]+" Configure the free GPU bridge token or hosted endpoint.")
    job_id=str(uuid.uuid4()); stamp=now()
    settings=request.model_dump() if hasattr(request,"model_dump") else request.dict()
    j={"job_id":job_id,"prompt":request.prompt,"status":"queued","created_at":stamp,"updated_at":stamp,"output":None,"error":None,"settings":settings,"progress":0,"stage":"Queued","started_at":None,"elapsed_seconds":0}
    with lock: jobs[job_id]=j
    persist(j)
    if not bridge_enabled: submitted[job_id]=executor.submit(worker,job_id,request)
    return {"job_id":job_id,"status":"queued","status_url":f"/jobs/{job_id}"}


def require_bridge_token(authorization):
    expected=os.getenv("CINEFORGE_FREE_GPU_BRIDGE_TOKEN","").strip()
    supplied=(authorization or "").removeprefix("Bearer ").strip()
    if not expected or not secrets.compare_digest(supplied,expected):
        raise HTTPException(status_code=401,detail="Invalid bridge credentials")

@app.get("/bridge/status")
def bridge_status():
    from datetime import datetime, timezone
    seen=None
    age=None
    if last_worker_seen:
        seen_dt=datetime.fromisoformat(last_worker_seen)
        age=max(0,(datetime.now(timezone.utc)-seen_dt).total_seconds())
    online=age is not None and age < 45
    return {"enabled":bool(os.getenv("CINEFORGE_FREE_GPU_BRIDGE_TOKEN")),"worker_online":online,"last_seen":last_worker_seen,"seconds_since_heartbeat":age}

@app.post("/bridge/heartbeat")
def bridge_heartbeat(authorization: str = Header(default="")):
    global last_worker_seen
    require_bridge_token(authorization)
    last_worker_seen = now()
    return {"worker_online": True, "last_seen": last_worker_seen}

@app.post("/bridge/claim")
def bridge_claim(authorization: str = Header(default="")):
    global last_worker_seen
    require_bridge_token(authorization)
    last_worker_seen = now()
    with lock:
        queued=sorted((j for j in jobs.values() if j["status"]=="queued"),key=lambda j:j["created_at"])
        if not queued: return {"job":None}
        job=queued[0]
        job.update(status="running",stage="GPU notebook claimed job",progress=1,started_at=now(),updated_at=now())
        snapshot=dict(job)
    persist(snapshot)
    return {"job":{"job_id":snapshot["job_id"],"prompt":snapshot["prompt"],"settings":snapshot["settings"]}}

@app.post("/bridge/result/{job_id}")
async def bridge_result(job_id: str, video: UploadFile = File(...), authorization: str = Header(default="")):
    require_bridge_token(authorization)
    if video.content_type not in ("video/mp4","application/octet-stream"):
        raise HTTPException(status_code=415,detail="Expected an MP4 upload")
    with lock:
        job=jobs.get(job_id)
        if not job: raise HTTPException(404,detail="Job not found")
        if job["status"]!="running": raise HTTPException(409,detail="Job is not running")
    path=OUTPUT_DIR/f"{job_id}.mp4"
    size=0
    header=bytearray()
    with path.open("wb") as out:
        while chunk:=await video.read(1024*1024):
            size+=len(chunk)
            if len(header)<12:
                header.extend(chunk[:12-len(header)])
            if size>500*1024*1024:
                out.close()
                path.unlink(missing_ok=True)
                raise HTTPException(413,detail="Video exceeds 500 MB limit")
            out.write(chunk)
    if size<128 or len(header)<12 or header[4:8]!=b"ftyp":
        path.unlink(missing_ok=True)
        raise HTTPException(400,detail="Upload is not a valid MP4 container")
    update_job(job_id,status="completed",stage="Complete",progress=100,output=str(path),error=None)
    return {"job_id":job_id,"status":"completed","bytes":size}

@app.post("/bridge/fail/{job_id}")
def bridge_fail(job_id: str, payload: dict, authorization: str = Header(default="")):
    require_bridge_token(authorization)
    with lock:
        if job_id not in jobs: raise HTTPException(404,detail="Job not found")
        if jobs[job_id]["status"]!="running": raise HTTPException(409,detail="Job is not running")
    update_job(job_id,status="failed",stage="GPU notebook failed",error=str(payload.get("error","Generation failed"))[:1000])
    return {"job_id":job_id,"status":"failed"}

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

@app.delete("/jobs/{job_id}")
def cancel_job(job_id:str):
    with lock:
        job=jobs.get(job_id)
        if not job: raise HTTPException(404,detail="Job not found")
        if job["status"]!="queued": raise HTTPException(409,detail="Only queued jobs can be cancelled")
        future=submitted.get(job_id)
        if future and not future.cancel(): raise HTTPException(409,detail="Job has already started")
        job.update(status="cancelled",error="Cancelled before execution",updated_at=now())
        snapshot=dict(job)
    persist(snapshot)
    return {"job_id":job_id,"status":"cancelled"}

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
