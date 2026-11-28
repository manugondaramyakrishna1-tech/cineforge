"""CineForge Free GPU Bridge worker for Kaggle/Colab notebooks.

Set CINEFORGE_API_URL and CINEFORGE_FREE_GPU_BRIDGE_TOKEN as notebook secrets
(or environment variables). Keep this notebook session running to accept jobs.
"""
import os, time, requests, torch
from pathlib import Path
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

API=os.environ["CINEFORGE_API_URL"].rstrip("/")
TOKEN=os.environ["CINEFORGE_FREE_GPU_BRIDGE_TOKEN"]
MODEL=os.getenv("CINEFORGE_MODEL","THUDM/CogVideoX-2b")
HEADERS={"Authorization":"Bearer "+TOKEN}
OUT=Path("cineforge_bridge_outputs"); OUT.mkdir(exist_ok=True)

def load_pipeline():
    if not torch.cuda.is_available():
        raise RuntimeError("No GPU detected. Enable GPU in Kaggle/Colab runtime settings.")
    print("CineForge GPU worker:",torch.cuda.get_device_name(0))
    pipe=CogVideoXPipeline.from_pretrained(MODEL,torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()
    return pipe

def process(pipe, job):
    jid=job["job_id"]; cfg=job.get("settings",{})
    path=OUT/(jid+".mp4")
    try:
        generator=torch.Generator(device="cuda").manual_seed(int(cfg.get("seed",42)))
        frames=pipe(prompt=job["prompt"],num_frames=int(cfg.get("frames",25)),
            num_inference_steps=int(cfg.get("steps",25)),
            guidance_scale=float(cfg.get("guidance",6.0)),generator=generator).frames[0]
        export_to_video(frames,str(path),fps=8)
        with path.open("rb") as f:
            response=requests.post(f"{API}/bridge/result/{jid}",headers=HEADERS,
                files={"video":("video.mp4",f,"video/mp4")},timeout=900)
        response.raise_for_status()
        print("Completed:",jid,response.json())
    except Exception as exc:
        try:
            requests.post(f"{API}/bridge/fail/{jid}",headers=HEADERS,
                json={"error":str(exc)[:900]},timeout=30).raise_for_status()
        except Exception as report_error:
            print("Could not report failure:",report_error)
        print("Job failed:",jid,exc)
    finally:
        path.unlink(missing_ok=True)

def run_worker():
    pipe=load_pipeline()
    print("Polling CineForge API. Stop the notebook cell to disconnect.")
    while True:
        try:
            response=requests.post(f"{API}/bridge/claim",headers=HEADERS,timeout=30)
            response.raise_for_status()
            job=response.json().get("job")
            if job:
                print("Claimed job:",job["job_id"])
                process(pipe,job)
            else:
                time.sleep(8)
        except KeyboardInterrupt:
            print("Worker stopped.")
            break
        except Exception as exc:
            print("Bridge connection error:",exc)
            time.sleep(15)

if __name__=="__main__":
    run_worker()
