"""Local CUDA or configured Hugging Face hosted endpoint text-to-video pipeline."""
import os, base64, requests
import torch
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

MODEL_ID = "THUDM/CogVideoX-2b"

def backend_status():
    endpoint=os.getenv("HF_ENDPOINT_URL","").strip()
    return {"backend":"huggingface_endpoint" if endpoint else "local_cuda",
            "endpoint_configured":bool(endpoint),"cuda_available":torch.cuda.is_available(),
            "hint":("Configured endpoint can run remotely." if endpoint else
                    "No HF_ENDPOINT_URL configured; local CUDA is required.")}

def generate_remote(prompt, output_path, model_id, num_frames, steps, guidance, seed):
    endpoint=os.getenv("HF_ENDPOINT_URL","").strip()
    if not endpoint: raise RuntimeError("HF_ENDPOINT_URL is not configured.")
    token=os.getenv("HF_TOKEN","").strip()
    headers={"Accept":"video/mp4"}
    if token: headers["Authorization"]="Bearer "+token
    payload={"inputs":prompt,"parameters":{"model_id":model_id,"num_frames":num_frames,
             "num_inference_steps":steps,"guidance_scale":guidance,"seed":seed}}
    response=requests.post(endpoint,json=payload,headers=headers,timeout=900)
    response.raise_for_status()
    content_type=response.headers.get("content-type","").lower()
    if "json" in content_type:
        data=response.json()
        encoded=data.get("video_base64") or data.get("video")
        if not encoded: raise RuntimeError("Endpoint JSON response must include video_base64 or video.")
        if encoded.startswith("data:"): encoded=encoded.split(",",1)[1]
        content=base64.b64decode(encoded)
    else: content=response.content
    if not content or len(content)<128: raise RuntimeError("Endpoint returned an empty or invalid video response.")
    with open(output_path,"wb") as out: out.write(content)
    return output_path

def load_model(model_id=MODEL_ID):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU unavailable. Configure HF_ENDPOINT_URL for hosted inference.")
    pipeline=CogVideoXPipeline.from_pretrained(model_id,torch_dtype=torch.float16)
    pipeline.enable_model_cpu_offload(); pipeline.vae.enable_tiling(); pipeline.vae.enable_slicing()
    return pipeline

def generate_video(prompt, output_path="outputs/video.mp4", model_id=MODEL_ID,
                   num_frames=25, steps=25, guidance=6.0, seed=42, progress_callback=None):
    if os.getenv("HF_ENDPOINT_URL","").strip():
        if progress_callback: progress_callback(0,steps)
        result=generate_remote(prompt,output_path,model_id,num_frames,steps,guidance,seed)
        if progress_callback: progress_callback(steps,steps)
        return result
    pipeline=load_model(model_id)
    generator=torch.Generator(device="cuda").manual_seed(seed)
    frames=pipeline(prompt=prompt,num_frames=num_frames,num_inference_steps=steps,
        guidance_scale=guidance,generator=generator,
        callback_on_step_end=(lambda pipe,step,timestep,kwargs:
          (progress_callback(step+1,steps) if progress_callback else None,kwargs)[1])).frames[0]
    export_to_video(frames,output_path,fps=8)
    return output_path

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("prompt");parser.add_argument("--output",default="outputs/video.mp4");parser.add_argument("--model",default=MODEL_ID);parser.add_argument("--frames",type=int,default=25);parser.add_argument("--steps",type=int,default=25);args=parser.parse_args()
    print(generate_video(args.prompt,args.output,args.model,args.frames,args.steps))
