from google.colab import userdata
import os

os.environ["CINEFORGE_API_URL"] = userdata.get("CINEFORGE_API_URL")
os.environ["CINEFORGE_FREE_GPU_BRIDGE_TOKEN"] = userdata.get("CINEFORGE_FREE_GPU_BRIDGE_TOKEN")

!wget -q https://raw.githubusercontent.com/manugondaramyakrishna1-tech/cineforge/main/free_gpu_bridge_worker.py -O free_gpu_bridge_worker.py
