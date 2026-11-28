# Deploy the GPU endpoint

1. Create a Hugging Face Docker Space and choose a GPU hardware tier available to your account.
2. Copy the files in this directory into that Space.
3. Configure the Space secret ENDPOINT_TOKEN with a strong secret.
4. Wait for the build and model load; check /health.
5. On CineForge server, set HF_ENDPOINT_URL to the Space URL ending in /generate.
6. Set HF_TOKEN to the same ENDPOINT_TOKEN secret.
7. Restart CineForge API and test generation.

The endpoint model is fixed by MODEL_ID (default THUDM/CogVideoX-2b). Endpoint requests use the CineForge payload contract. Keep credentials server-side only.
