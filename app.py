import os, requests, streamlit as st
from pathlib import Path

st.set_page_config(page_title="CineForge Model Pipeline", page_icon="🎬", layout="centered")
st.title("🎬 CineForge — Model Pipeline")
st.caption("Prompt → Hugging Face video inference → MP4 output")

token = st.text_input("Hugging Face access token", type="password", value=os.getenv("HF_TOKEN",""))
model = st.text_input("Model ID", value=os.getenv("HF_VIDEO_MODEL","Lightricks/LTX-Video"))
prompt = st.text_area("Video prompt", placeholder="Describe your scene, camera movement, lighting and style...")
duration = st.slider("Requested duration (seconds)", 2, 8, 4)
st.info("Model availability, supported parameters and limits depend on the selected Hugging Face provider/model.")

if st.button("Generate video", type="primary", disabled=not (token and prompt.strip())):
    with st.spinner("Submitting inference request…"):
        try:
            url = "https://router.huggingface.co/hf-inference/models/" + model.strip()
            headers = {"Authorization": "Bearer " + token.strip(), "Content-Type":"application/json"}
            payload = {"inputs": prompt.strip(), "parameters":{"num_frames": int(duration*8)}}
            response = requests.post(url, headers=headers, json=payload, timeout=600)
            if not response.ok:
                st.error(f"Inference failed ({response.status_code}).")
                st.code(response.text[:1500])
            elif "video" not in response.headers.get("content-type","").lower() and not response.content[:4] == b"\x00\x00\x00\x":
                st.warning("The response may not be an MP4. Response type: " + response.headers.get("content-type","unknown"))
                st.code(response.text[:500] if len(response.content)<5000 else "Non-text response received.")
            else:
                output = Path("outputs"); output.mkdir(exist_ok=True)
                path = output / "generated_video.mp4"
                path.write_bytes(response.content)
                st.success("Video output saved.")
                st.video(response.content)
                st.download_button("Download MP4", response.content, "cineforge.mp4", "video/mp4")
        except requests.exceptions.Timeout:
            st.error("Request timed out. Try a shorter prompt or a provider/model with faster inference.")
        except Exception as e:
            st.error(f"Pipeline error: {e}")
st.markdown("---")
st.caption("Token is entered in-session and is not written to the repository. Check the model card for provider support and licensing.")
