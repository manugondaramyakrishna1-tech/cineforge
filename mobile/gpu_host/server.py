import os, threading, uuid, traceback
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app=FastAPI(title="CineForge Local GPU Bridge")
TOKEN=os.getenv("CINEFORGE_MOBILE_TOKEN","")
jobs={}
pipeline=None
lock=threading.Lock()

def auth(value):
    if not TOKEN: raise HTTPException(503,"Set CINEFORGE_MOBILE_TOKEN on the host first.")
    if not value or value.removeprefix("Bearer ").strip()!=TOKEN:
        raise HTTPException(401,"Unauthorized")

def load_pipeline():
    global pipeline
    with lock:
        if pipeline is not None: return pipeline
        import torch
        from diffusers import CogVideoXPipeline
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA GPU not detected. This bridge currently requires NVIDIA CUDA.")
        pipeline=CogVideoXPipeline.from_pretrained("THUDM/CogVideoX-2b",torch_dtype=torch.float16)
        pipeline.to("cuda")
        pipeline.enable_model_cpu_offload()
        return pipeline

class RenderRequest(BaseModel):
    prompt:str=Field(min_length=1,max_length=2000)

def worker(jid,prompt):
    jobs[jid]["status"]="loading_model"
    try:
        pipe=load_pipeline()
        jobs[jid]["status"]="generating"
        import torch, av
        frames=pipe(prompt,num_frames=49,num_inference_steps=30).frames[0]
        os.makedirs("outputs",exist_ok=True)
        path=os.path.abspath(os.path.join("outputs",jid+".mp4"))
        container=av.open(path,"w")
        stream=container.add_stream("libx264",rate=8)
        stream.width=frames[0].shape[1]; stream.height=frames[0].shape[0]
        stream.pix_fmt="yuv420p"
        for f in frames:
            import numpy as np
            arr=np.asarray(f)
            if arr.dtype!=np.uint8: arr=(arr*255).clip(0,255).astype(np.uint8)
            vf=av.VideoFrame.from_ndarray(arr,format="rgb24")
            for packet in stream.encode(vf): container.mux(packet)
        for packet in stream.encode(): container.mux(packet)
        container.close()
        jobs[jid].update(status="completed",video_path=path)
    except Exception as e:
        jobs[jid].update(status="failed",error=str(e)[:500])

@app.get("/api/mobile/health")
def health(authorization:Optional[str]=Header(default=None)):
    auth(authorization)
    try:
        import torch
        gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CUDA GPU unavailable"
    except Exception as e: gpu=str(e)
    return {"service":"CineForge GPU Bridge","status":"online","gpu":gpu,"inference":"CogVideoX-2b","model_loaded":pipeline is not None}

@app.post("/api/mobile/render",status_code=202)
def render(req:RenderRequest,authorization:Optional[str]=Header(default=None)):
    auth(authorization)
    jid=str(uuid.uuid4())
    jobs[jid]={"id":jid,"status":"queued","prompt":req.prompt}
    threading.Thread(target=worker,args=(jid,req.prompt),daemon=True).start()
    return {"id":jid,"status":"queued","message":"Render job queued"}

@app.get("/api/mobile/jobs/{jid}")
def job(jid:str,authorization:Optional[str]=Header(default=None)):
    auth(authorization)
    if jid not in jobs: raise HTTPException(404,"Job not found")
    return jobs[jid]
