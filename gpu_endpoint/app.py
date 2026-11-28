import os, secrets, tempfile
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

MODEL_DEFAULT=os.getenv("MODEL_ID","THUDM/CogVideoX-2b")
TOKEN=os.getenv("ENDPOINT_TOKEN","")
app=FastAPI(title="CineForge GPU endpoint")
pipeline=None
class Parameters(BaseModel):
 model_id:str=MODEL_DEFAULT
 num_frames:int=Field(default=25,ge=17,le=49)
 num_inference_steps:int=Field(default=25,ge=1,le=50)
 guidance_scale:float=Field(default=6.0,ge=1,le=10)
 seed:int=Field(default=42,ge=0,le=9999999)
class Request(BaseModel):
 inputs:str=Field(min_length=3,max_length=2000)
 parameters:Parameters=Parameters()
@app.on_event("startup")
def load():
 global pipeline
 if not torch.cuda.is_available(): raise RuntimeError("Attached CUDA GPU required.")
 pipeline=CogVideoXPipeline.from_pretrained(MODEL_DEFAULT,torch_dtype=torch.float16)
 pipeline.enable_model_cpu_offload();pipeline.vae.enable_tiling();pipeline.vae.enable_slicing()
def authorize(header):
 if TOKEN and not secrets.compare_digest(header or "", "Bearer "+TOKEN): raise HTTPException(401,"Unauthorized")
@app.get("/health")
def health(): return {"ready":pipeline is not None,"cuda":torch.cuda.is_available(),"model":MODEL_DEFAULT}
@app.post("/generate")
def generate(req:Request,authorization:str|None=Header(default=None)):
 authorize(authorization)
 if pipeline is None: raise HTTPException(503,"Model not ready")
 p=req.parameters
 if p.model_id!=MODEL_DEFAULT: raise HTTPException(400,"Server model only.")
 try:
  generator=torch.Generator(device="cuda").manual_seed(p.seed)
  frames=pipeline(prompt=req.inputs,num_frames=p.num_frames,num_inference_steps=p.num_inference_steps,guidance_scale=p.guidance_scale,generator=generator).frames[0]
  path=tempfile.mktemp(suffix=".mp4")
  export_to_video(frames,path,fps=8)
  return FileResponse(path,media_type="video/mp4",filename="cineforge.mp4")
 except Exception as e: raise HTTPException(500,str(e))
