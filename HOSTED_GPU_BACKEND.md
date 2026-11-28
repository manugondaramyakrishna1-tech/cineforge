# Hosted GPU backend configuration

CineForge now supports an optional remote inference endpoint configured by environment variables.

- `HF_ENDPOINT_URL`: URL for a compatible hosted inference endpoint that accepts the CineForge request payload and returns MP4 bytes, or JSON containing `video_base64` (or `video` as base64).
- `HF_TOKEN`: optional bearer token for a protected endpoint. Keep this secret server-side; do not put it into mobile.html or client code.

Example environment setup (replace values with your own endpoint and token):

```bash
export HF_ENDPOINT_URL="https://your-endpoint.example/generate"
export HF_TOKEN="your-secret-token"
uvicorn api:app --host 0.0.0.0 --port 8000
```

Endpoint payload:

```json
{"inputs":"prompt text","parameters":{"model_id":"THUDM/CogVideoX-2b","num_frames":25,"num_inference_steps":25,"guidance_scale":6.0,"seed":42}}
```

Endpoint must implement this payload contract and return MP4 bytes or JSON with a base64 video. This is not a generic Hugging Face Hub URL: it must be an actual deployed inference endpoint with video generation support and GPU resources. Endpoint pricing/availability and model licensing are provider-dependent.

Without this setting, CineForge uses local CUDA. The remote endpoint path is configured but not yet verified against a real hosted endpoint.
