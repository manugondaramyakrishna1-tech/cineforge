from fastapi import FastAPI
app=FastAPI(title="CineForge GPU Bridge")

@app.get("/api/mobile/health")
def health():
    gpu="unavailable"
    try:
        import torch
        if torch.cuda.is_available(): gpu=torch.cuda.get_device_name(0)
        elif hasattr(torch.backends,"mps") and torch.backends.mps.is_available(): gpu="Apple MPS"
    except ImportError:
        gpu="PyTorch not installed"
    return {"service":"CineForge GPU Bridge","status":"online","gpu":gpu,"inference":"not_connected"}

@app.post("/api/mobile/render")
def render(req:dict):
    prompt=str(req.get("prompt","")).strip()
    if not prompt: return {"status":"invalid","message":"Prompt is required."}
    return {"status":"not_ready","message":"Bridge received your request, but the local inference engine is not connected yet."}
